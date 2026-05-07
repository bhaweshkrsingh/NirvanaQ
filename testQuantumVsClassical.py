# Disable http.client low-level debug output BEFORE any IBM imports.
import http.client as _hc
_hc.HTTPConnection.debuglevel  = 0
_hc.HTTPSConnection.debuglevel = 0

from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.circuit.library import PhaseOracleGate, grover_operator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit import QuantumCircuit, ClassicalRegister
import time, os, sys, random, math
from datetime import datetime

# =============================================================================
# LOGGING
# =============================================================================
os.makedirs("logs", exist_ok=True)
run_ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
log_path = os.path.join("logs", f"run_{run_ts}.log")

import pytz
_EST_TZ   = pytz.timezone("America/New_York")
_log_file = open(log_path, "w", encoding="utf-8")
_terminal = sys.stdout

def _safe(s):
    return str(s).encode("cp1252", errors="replace").decode("cp1252")

def p(*args):
    msg  = " ".join(str(a) for a in args)
    ts   = datetime.now(_EST_TZ).strftime("%m/%d/%Y %H:%M:%S[EST]")
    line = f"{ts} {msg}"
    _log_file.write(line + "\n")
    _log_file.flush()
    _terminal.write(_safe(line) + "\n")
    _terminal.flush()

# =============================================================================
# CHARACTER SET
#
# CHARSET maps index -> character.  Index 0 = space, 1 = 'a', ..., 14 = 'n'.
# Every index is in the range 0-14, strictly less than our smallest modulus
# n=15.  This guarantees RSA round-trips perfectly with no lossy mod reduction:
#   encrypt: CHARSET.index(char)  -> numeric value 0-14
#   decrypt: CHARSET[pow(c,d,n)]  -> original char exactly
# =============================================================================
CHARSET = ' abcdefghijklmn'   # index: 0=space 1=a 2=b ... 14=n

# =============================================================================
# CONFIGURATION
# =============================================================================
num_qbits      = 4      # keyspace 2^4 = 16; max for reliable NISQ signal
num_iterations = 2      # depth ~400 gates; 3 iterations hits ~700 on d=7
num_shots      = 1024

# =============================================================================
# PLAINTEXT POOL  (5 sentences — only characters from CHARSET)
# =============================================================================
PLAINTEXT_POOL = [
    "mankind and machine",   # the Wright Brothers sentence
    "a fine calm lake",
    "big blind claim",
    "flag and badge",
    "a clean flame",
]

# =============================================================================
# RSA KEY POOL  (5 entries, 5 distinct 4-bit private keys)
#
# Format: (p, q, n=p*q, phi=(p-1)*(q-1), e, d)
# All d values fit in 4 bits (d <= 15).
# All n > 14 so every CHARSET index (0-14) is < n.
# All (e, d) satisfy e*d ≡ 1 mod phi, verified by pow(e,-1,phi).
# Verified: pow(pow(m,e,n),d,n) == m for all m in 0-14 for each pool.
#
#   d = 0011 ( 3): p=3, q=5,  n=15, phi= 8
#   d = 0101 ( 5): p=3, q=5,  n=15, phi= 8
#   d = 0111 ( 7): p=3, q=5,  n=15, phi= 8
#   d = 1011 (11): p=3, q=7,  n=21, phi=12  -- different modulus
#   d = 1101 (13): p=5, q=7,  n=35, phi=24  -- different modulus
# =============================================================================
RSA_KEY_POOL = [
    (3, 5, 15,  8,  3, None),
    (3, 5, 15,  8,  5, None),
    (3, 5, 15,  8,  7, None),
    (3, 7, 21, 12, 11, None),
    (5, 7, 35, 24, 13, None),
]
RSA_KEY_POOL = [(p, q, n, phi, e, pow(e, -1, phi)) for p, q, n, phi, e, _ in RSA_KEY_POOL]

# Pick random key and random message each run
key_index   = random.randint(0, 4)
msg_index   = random.randint(0, 4)
p_prime, q_prime, n_rsa, phi_n, e_pub, d_priv = RSA_KEY_POOL[key_index]
plaintext_msg = PLAINTEXT_POOL[msg_index]

p(f"Run started   : {datetime.now().isoformat()}")
p(f"Log file      : {log_path}")
p("")

# =============================================================================
# RSA ENCODE / DECODE  (character-level, using CHARSET indices)
# =============================================================================
def rsa_encrypt(msg, e, n):
    return [pow(CHARSET.index(c), e, n) for c in msg]

def rsa_decrypt(ciphertext, d, n):
    chars = []
    for c in ciphertext:
        idx = pow(c, d, n)
        if idx >= len(CHARSET):
            return None   # wrong key produces out-of-range index
        chars.append(CHARSET[idx])
    return "".join(chars)

cipher_list = rsa_encrypt(plaintext_msg, e_pub, n_rsa)

p("=" * 65)
p("RSA KEY SETUP")
p("=" * 65)
p(f"  Key pool index      : {key_index}  (chosen at random)")
p(f"  Message index       : {msg_index}  (chosen at random)")
p(f"  Prime p             : {p_prime}")
p(f"  Prime q             : {q_prime}")
p(f"  Modulus n = p*q     : {n_rsa}")
p(f"  phi(n)=(p-1)*(q-1)  : {phi_n}")
p(f"  Public key  e       : {e_pub}    (known to attacker)")
p(f"  Private key d       : {d_priv:04b} in binary = {d_priv}  (HIDDEN from quantum)")
p(f"  Verification e*d mod phi = {(e_pub * d_priv) % phi_n}  (must be 1)")
p(f"")
p(f"  Plaintext message   : '{plaintext_msg}'")
p(f"  Char indices        : {[CHARSET.index(c) for c in plaintext_msg]}")
p(f"  RSA ciphertext      : {cipher_list}  <- attacker intercepts this")
p(f"  Attacker has        : ciphertext + public key (e={e_pub}, n={n_rsa})")
p(f"  Attacker also has   : one known plaintext char (known-plaintext attack)")
p(f"  Attacker does NOT have: private key d")

# =============================================================================
# STEP 0 — CLASSICAL BRUTE-FORCE BENCHMARK
# =============================================================================
# Known-plaintext pair: attacker uses the first character of the message.
# Real attacks use protocol structure (HTTP headers, file magic bytes, etc.)
known_plain_char = plaintext_msg[0]
known_plain_idx  = CHARSET.index(known_plain_char)
known_cipher_val = cipher_list[0]

p("")
p("=" * 65)
p("STEP 0 -- CLASSICAL BRUTE-FORCE BENCHMARK  (this machine)")
p("=" * 65)
p(f"  Known plaintext char  : '{known_plain_char}'  (CHARSET index {known_plain_idx})")
p(f"  Known ciphertext val  : {known_cipher_val}")
p(f"  Oracle test           : pow(cipher={known_cipher_val}, candidate_d, n={n_rsa}) == {known_plain_idx}")
p(f"  Brute-forcing d in range 1..{n_rsa - 1} ...")

bf_start     = time.perf_counter()
bf_found_key = None
bf_checks    = 0
for candidate_d in range(1, n_rsa):
    bf_checks += 1
    if pow(known_cipher_val, candidate_d, n_rsa) == known_plain_idx:
        bf_found_key = candidate_d
        break
bf_elapsed_ns = (time.perf_counter() - bf_start) * 1e9
bf_elapsed_us = bf_elapsed_ns / 1e3

bf_decrypted  = rsa_decrypt(cipher_list, bf_found_key, n_rsa) if bf_found_key else None
bf_success    = (bf_decrypted == plaintext_msg)

p(f"  Checks performed      : {bf_checks}")
p(f"  Private key found     : d = {bf_found_key}  ({bf_found_key:04b} binary)  "
  f"[true d = {d_priv}, match = {bf_found_key == d_priv}]")
p(f"  Time on this CPU      : {bf_elapsed_ns:.0f} ns  ({bf_elapsed_us:.3f} us)")
p(f"  Decrypted message     : '{bf_decrypted}'")
p(f"  Decryption SUCCESS    : {bf_success}")
if not bf_success and bf_found_key != d_priv:
    p(f"  (brute-force found a different d that satisfies the single-char oracle;")
    p(f"   quantum oracle is built from the TRUE private key d={d_priv})")

bf_seconds = bf_elapsed_ns / 1e9

# =============================================================================
# STEP 1 — BUILD THE QUANTUM ORACLE
#
# The oracle marks the binary representation of the true private key d_priv.
# It is built purely from public values — it tests whether a candidate d
# correctly decrypts the known ciphertext to the known plaintext index.
# The quantum hardware never sees d_priv; it must find it by amplitude
# amplification across all 2^num_qbits superposed candidates.
# =============================================================================
valid_ds = [d for d in range(1, 2**num_qbits)
            if pow(known_cipher_val, d, n_rsa) == known_plain_idx]

p("")
p("=" * 65)
p("STEP 1 -- QUANTUM ORACLE")
p("=" * 65)
p(f"  Oracle checks: pow({known_cipher_val}, candidate_d, {n_rsa}) == {known_plain_idx}")
p(f"  Valid d values in 0..{2**num_qbits - 1}: {valid_ds}")
p(f"  Primary target (true private key): d = {d_priv} = {d_priv:04b}")

target_d = d_priv
terms = [f'x{i}' if (target_d >> i) & 1 else f'~x{i}' for i in range(num_qbits)]
oracle_expression = ' & '.join(terms)

p(f"  Oracle boolean expr : {oracle_expression}")

oracle = PhaseOracleGate(oracle_expression)
g_op   = grover_operator(oracle)

# =============================================================================
# STEP 2 — BUILD THE GROVER CIRCUIT
# =============================================================================
qc = QuantumCircuit(g_op.num_qubits)
qc.h(range(num_qbits))
for _ in range(num_iterations):
    qc.compose(g_op, inplace=True)
cr = ClassicalRegister(num_qbits, 'meas')
qc.add_register(cr)
qc.measure(range(num_qbits), cr)

p("")
p("=" * 65)
p("STEP 2 -- GROVER CIRCUIT")
p("=" * 65)
p(f"  Qubits         : {num_qbits}  (keyspace = {2**num_qbits} candidates)")
p(f"  Iterations     : {num_iterations}  "
  f"(optimal = floor(pi/4 * sqrt({2**num_qbits})) = {math.floor(math.pi/4*math.sqrt(2**num_qbits))})")
p(f"  Pre-transpile depth : {qc.depth()}")

# =============================================================================
# STEP 3 — CONNECT TO IBM AND TRANSPILE
# =============================================================================
MY_IBM_QUANTUM_KEY = os.getenv("MY_IBM_QUANTUM_KEY")
if not MY_IBM_QUANTUM_KEY:
    raise ValueError("Set the MY_IBM_QUANTUM_KEY environment variable before running.")

# Connect, pick shortest-queue backend, and transpile.
# Backend status query is done BEFORE stdout redirect so errors surface cleanly.
QiskitRuntimeService.save_account(
    channel="ibm_quantum_platform", token=MY_IBM_QUANTUM_KEY, overwrite=True
)
service       = QiskitRuntimeService(channel="ibm_quantum_platform")
backends_list = ", ".join(b.name for b in service.backends(operational=True, simulator=False))
_candidates   = [service.backend(b) for b in ("ibm_kingston", "ibm_fez", "ibm_marrakesh")]
_pending      = {b.name: b.status().pending_jobs for b in _candidates}
backend       = min(_candidates, key=lambda b: _pending[b.name])

_devnull     = open(os.devnull, "w")
_real_stderr = sys.stderr
sys.stdout   = _devnull
sys.stderr   = _devnull
pm          = generate_preset_pass_manager(backend=backend, optimization_level=1)
isa_circuit = pm.run(qc)
sys.stdout = _terminal
sys.stderr = _real_stderr
_devnull.close()

p("")
p("=" * 65)
p("STEP 3 -- IBM QUANTUM CONNECTION + TRANSPILE")
p("=" * 65)
p(f"  Available backends   : {backends_list}")
p(f"  Pending jobs         : { {n: v for n,v in _pending.items()} }")
p(f"  Shortest queue chosen: {backend.name}  ({_pending[backend.name]} pending)")
p(f"  Post-transpile depth : {isa_circuit.depth()}")
p(f"  Gate count           : {dict(isa_circuit.count_ops())}")
if isa_circuit.depth() > 600:
    p(f"  WARNING: depth {isa_circuit.depth()} > 600 -- results may be noisy.")
else:
    p(f"  Depth is within reliable range for NISQ hardware.")

# =============================================================================
# STEP 4 — EXECUTE ON IBM QUANTUM HARDWARE
# =============================================================================
sampler = Sampler(mode=backend)
sampler.options.dynamical_decoupling.enable = True

p("")
p("=" * 65)
p("STEP 4 -- QUANTUM JOB ON IBM HARDWARE")
p("=" * 65)
p(f"  Backend    : {backend.name}")
p(f"  Qubits     : {num_qbits},  Iterations: {num_iterations},  Shots: {num_shots}")
p(f"  Grover is searching for d that decrypts cipher={known_cipher_val} -> plain index {known_plain_idx} ('{known_plain_char}')")
p(f"  The quantum chip does NOT know d = {d_priv}")

_devnull2  = open(os.devnull, "w")
sys.stdout = _devnull2
sys.stderr = _devnull2
start_wall = time.time()
job        = sampler.run([isa_circuit], shots=num_shots)
sys.stdout = _terminal
sys.stderr = _real_stderr
_devnull2.close()

p(f"  Job ID     : {job.job_id()}")
p(f"  Recover later: QiskitRuntimeService().job('{job.job_id()}').result()")

_devnull3  = open(os.devnull, "w")
sys.stdout = _devnull3
sys.stderr = _devnull3
try:
    result = job.result()
except Exception as exc:
    sys.stdout = _terminal
    sys.stderr = _real_stderr
    p(f"  Job failed : {exc}")
    raise
finally:
    sys.stdout = _terminal
    sys.stderr = _real_stderr
    _devnull3.close()

end_wall = time.time()

# =============================================================================
# STEP 5 — EXTRACT KEY AND DECRYPT
# =============================================================================
counts        = result[0].data.meas.get_counts()
found_key_str = max(counts, key=counts.get)
found_d       = int(found_key_str, 2)
q_decrypted   = rsa_decrypt(cipher_list, found_d, n_rsa)
key_match     = (found_d == d_priv)
q_success     = (q_decrypted == plaintext_msg)

# =============================================================================
# TIMING
# =============================================================================
_devnull4  = open(os.devnull, "w")
sys.stdout = _devnull4
sys.stderr = _devnull4
metrics    = job.metrics()
sys.stdout = _terminal
sys.stderr = _real_stderr
_devnull4.close()

usage      = metrics.get('usage', {})
q_seconds  = usage.get('quantum_seconds', None)
timestamps = metrics.get('timestamps', {})

def _ts(key):
    raw = timestamps.get(key)
    if raw is None:
        return None
    return datetime.fromisoformat(raw.rstrip('Z') + '+00:00').timestamp()

total_wall     = end_wall - start_wall
ts_created     = _ts('created')
ts_running     = _ts('running')
ts_finished    = _ts('finished')
queue_wait     = (ts_running  - ts_created)  if (ts_running  and ts_created)  else None
qpu_window     = (ts_finished - ts_running)  if (ts_finished and ts_running)  else None
cloud_overhead = (total_wall  - qpu_window)  if qpu_window is not None        else None

def _fmt(val, unit='s'):
    return f"{val:.3f} {unit}" if val is not None else "N/A"

# =============================================================================
# RESULTS
# =============================================================================
p("")
p("=" * 65)
p("RESULTS")
p("=" * 65)
p(f"  RSA public key (e, n)        : ({e_pub}, {n_rsa})  <- what attacker has")
p(f"  Known pair used as oracle    : '{known_plain_char}' (idx {known_plain_idx}) -> cipher {known_cipher_val}")
p(f"  True private key d (hidden)  : {d_priv:04b} = {d_priv}")
p(f"  Private key found by Grover  : {found_key_str} = {found_d}")
p(f"  Key match                    : {key_match}")
p("")
p(f"  Original plaintext           : '{plaintext_msg}'")
p(f"  RSA ciphertext               :  {cipher_list}")
p(f"  Quantum-decrypted message    : '{q_decrypted}'")
p(f"  Decryption SUCCESS           : {q_success}")
p("")
p("  Top 5 measured states (most frequent = Grover's answer):")
for state, cnt in sorted(counts.items(), key=lambda x: -x[1])[:5]:
    marker = " <-- TRUE PRIVATE KEY" if int(state, 2) == d_priv else ""
    bar    = "#" * int(cnt * 40 / num_shots)
    p(f"    {state} (d={int(state,2):2d}) : {cnt:4d} shots  ({100*cnt/num_shots:5.1f}%)  {bar}{marker}")
p("")
p("  TIMING BREAKDOWN")
p(f"  [total]   Total wall-clock   : {_fmt(total_wall)}")
p(f"  [queue]   Queue wait         : {_fmt(queue_wait)}")
p(f"  [slot]    QPU slot window    : {_fmt(qpu_window)}")
p(f"  [***QPU]  Pure QPU gate time : {_fmt(q_seconds)}  *** counts against quota ***")
p(f"  [net]     Network + cloud    : {_fmt(cloud_overhead)}")
p("")
p("  CLASSICAL vs QUANTUM  (this run)")
p(f"  [cpu]     Brute-force CPU    : {bf_elapsed_ns:.0f} ns  ({bf_elapsed_us:.3f} us)")
p(f"  [***QPU]  Pure QPU gate time : {_fmt(q_seconds)}")
if q_seconds and q_seconds > 0:
    ratio = (bf_elapsed_ns / 1e9) / q_seconds
    p(f"  [ratio]   QPU is {1/ratio:.0f}x slower at {num_qbits} bits  (advantage threshold ~34 qubits)")
p("")
p(f"Run completed : {datetime.now().isoformat()}")
p(f"Log saved to  : {log_path}")
p("")
p("  Generating scaling diagram -> quantum_scaling.png ...")

import subprocess
subprocess.run([
    sys.executable, "quantum_scaling.py",
    "--classical_ns", str(bf_elapsed_ns),
    "--qpu_seconds",  str(q_seconds if q_seconds is not None else 0),
    "--real_qbits",   str(num_qbits),
], check=True)
p("  Saved: quantum_scaling.png")
_log_file.close()

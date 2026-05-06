# I Ran Grover's Algorithm on IBM's 156-Qubit Quantum Computer to Crack RSA. Here's What Actually Happened.

*A developer's field report from the edge of what quantum hardware can actually do today.*

---

## The Wright Brothers Moment

The first Wright Brothers flight at Kitty Hawk in 1903 did not travel faster or further than a horse and carriage. By every practical measure of the day, it lost. The horse won. But December 17, 1903 proved something more important than speed: it proved that an entirely new method of travel was physically possible — and that the trajectory of that method, not its current performance, was what mattered.

Quantum computing is at Kitty Hawk right now.

I got free access to IBM's real quantum hardware — a 156-qubit IBM Heron r2 processor called ibm_kingston — and I spent my allocation running Grover's algorithm against toy RSA encryption. Not a simulation. Not a demo. Actual gate operations on actual superconducting qubits in a dilution refrigerator.

Here is exactly what happened, what worked, what catastrophically didn't, and what it means for the encrypted data sitting on adversarial servers right now.

---

## What Is Grover's Algorithm and Why Should Cryptographers Lose Sleep Over It?

Classical computers search an unsorted list of N items in O(N) time. In the worst case, you check every item. For a 256-bit RSA key, the keyspace is 2^256 — roughly 10^77 possible values. Classical brute-force is not just impractical; it is cosmologically impossible within the lifetime of the universe.

Grover's algorithm, published by Lov Grover in 1996, changes the scaling. A quantum computer running Grover's algorithm finds the target item in O(√N) steps. That square root is the threat. It doesn't eliminate the keyspace — it takes the square root of it.

Run the numbers:

| Key size | Classical brute-force | Grover's algorithm |
|----------|-----------------------|--------------------|
| 4 bits   | 16 attempts           | 3 iterations       |
| 20 bits  | 1,048,576 attempts    | 804 iterations     |
| 256 bits | 10^77 attempts        | ~10^38 iterations  |

A 256-bit key still requires ~10^38 Grover iterations. That is not crackable today or anytime soon. But a 20-bit key collapses from a million attempts to 804. And the scaling curve matters: every time we double the number of reliable logical qubits, the effective key protection halves in computational cost.

The attack scenario that makes this relevant right now is known as "store now, decrypt later." Adversaries — nation-states, well-resourced criminal groups — are harvesting encrypted internet traffic today and archiving it. They cannot read it yet. They are waiting for quantum hardware to mature. When it does, any data encrypted with pre-quantum standards that was intercepted in 2024 or 2025 becomes readable retroactively. Medical records. Legal communications. Financial transactions. State secrets.

This is not a theoretical concern. NIST treated it as a real and present threat and finalized post-quantum cryptographic standards in 2024.

---

## The Experiment: A Known-Plaintext Attack on Toy RSA

The project is called NirvanaQ. The goal was to implement a real known-plaintext attack on RSA using Grover's algorithm and run it on live IBM quantum hardware — not a simulator, not a local emulation.

A known-plaintext attack works like this: the attacker possesses one plaintext/ciphertext pair. In practice, this is trivially available. HTTP/1.1 responses always start with "HTTP/1.1 200 OK". PDF files always start with "%PDF-". These known headers act as levers. If you can use the known plaintext to verify a candidate key, you can run Grover's algorithm to find the key, then use it to decrypt every other message encrypted under the same key.

For the experiment, we defined a small RSA key pool — five key pairs built from small primes:

| Pool | p | q |  n | phi |  e |  d |
|------|---|---|----|-----|----|----|
|  0   | 3 | 5 | 15 |   8 |  3 |  3 |
|  1   | 3 | 5 | 15 |   8 |  5 |  5 |
|  2   | 3 | 5 | 15 |   8 |  7 |  7 |
|  3   | 3 | 7 | 21 |  12 | 11 | 11 |
|  4   | 5 | 7 | 35 |  24 | 13 | 13 |

Each run, the system picks a key pair at random. The private key `d` is hidden from the quantum circuit — the circuit only sees the public key and one ciphertext/plaintext pair. Grover's job is to find `d`.

Five plaintext messages were also defined, also picked at random each run:

1. "mankind and machine"
2. "a fine calm lake"
3. "big blind claim"
4. "flag and badge"
5. "a clean flame"

The tech stack: Python, Qiskit 2.x, qiskit-ibm-runtime, PhaseOracleGate, grover_operator, SamplerV2, generate_preset_pass_manager, with dynamical decoupling enabled.

---

## The Hard Wall: Circuit Depth and Decoherence

This is where the experiment got humbling.

Qubits are not stable. They lose their quantum state — they decohere — after a certain number of gate operations. The exact limit depends on the hardware, but on current IBM public hardware, coherence breaks down after roughly a few hundred to a couple thousand gate operations in practice. Run a circuit deeper than that and you get noise, not computation.

The ibm_kingston chip uses a heavy-hex qubit topology. This means each qubit connects to only 2–3 physical neighbors. This sounds like a minor hardware detail. It is not. It is the crux of why scaling is so hard right now.

When you write a quantum circuit, you describe multi-qubit operations between logical qubits that may not be physically adjacent on the chip. Before the circuit can run, a transpiler must route those operations through the actual chip topology. When qubits are not neighbors, the transpiler inserts SWAP gates to physically move qubit states across the chip until they are adjacent. Each SWAP is itself three two-qubit gates. On a heavy-hex topology with limited connectivity, SWAP chains can be very long.

The result: a circuit that looks modest at the logical level explodes in depth after transpilation.

Here is what we actually measured:

| Qubits | Grover iters | Post-transpile depth | Result |
|--------|-------------|----------------------|--------|
| 10     | 25 (optimal)| ~120,000             | Pure noise |
| 10     | 3           | ~14,000              | Pure noise |
| 4      | 3           | ~700 (on d=7)        | Marginal |
| 4      | 2           | ~394                 | Signal survives |

A 10-qubit circuit with just 3 Grover iterations produces a post-transpile depth of 14,000 gates. The qubits decohere long before the circuit finishes. The output is indistinguishable from random noise.

The maximum reliable configuration on current IBM public hardware: 4 qubits, 2 Grover iterations.

---

## How We Made It Work: The 4-Qubit Solution and the CHARSET Trick

Getting a successful result on 4 qubits required solving one additional non-obvious problem: the character encoding.

Standard ASCII encodes characters as integers. The letter 'H' is 72. 'e' is 101. But our toy RSA has modulus n=15. RSA encryption computes `ciphertext = plaintext^e mod n`. If the plaintext value is larger than n — say, ASCII 'H' = 72, and n = 15 — the modular reduction discards information. You cannot recover the original value. The math breaks.

The solution: define a custom 15-character alphabet:

```
CHARSET = ' abcdefghijklmn'
```

Space maps to 0. 'a' maps to 1. 'b' maps to 2. Up to 'n' which maps to 14. Every index is strictly below n=15. RSA round-trips perfectly. The quantum-found key decrypts the full message back to the exact original string with no approximations, no workarounds.

This is not a limitation of the approach — it is what you do in any real protocol: define an encoding that fits your modulus. In real RSA at scale, the message is padded and chunked properly. Here, the custom charset is the minimal version of that discipline.

---

## The Real Results: Numbers From a Live Run

Here is a complete, unedited run. Key pool 2 was selected at random. Message index 0 was selected at random.

```
Key pool index      : 2  (chosen at random)
Message index       : 0  (chosen at random)
Prime p=3, q=5, n=15, phi=8, e=7
Private key d       : 0111 = 7  (HIDDEN from quantum)

Plaintext message   : 'mankind and machine'
RSA ciphertext      : [13, 1, 14, 6, 9, 14, 4, 0, 1, 14, 4, 0, 13, 1, 3, 8, 9, 14, 5]

True private key d  : 0111 = 7
Private key found by Grover : 0111 = 7
Key match           : True

Quantum-decrypted message : 'mankind and machine'
Decryption SUCCESS  : True

Top measured state  : 0111 (d=7) : 590 shots (57.6%)  <-- TRUE PRIVATE KEY

Pure QPU gate time  : 2.1 seconds  *** counts against quota ***
Queue wait          : ~3 seconds
Post-transpile depth: 394 gates
```

State `0111` — the correct private key — appeared in 57.6% of all measurement shots. The next most frequent states were noise. The algorithm converged. The key was found. The message was decrypted.

The free tier gives you 10 minutes of pure QPU time per month. Each run consumes about 2 seconds of that quota. Queue wait time (1–5 seconds) does not count against the quota. Total wall-clock per run is 8–17 seconds.

Three backends were available: ibm_fez, ibm_marrakesh, and ibm_kingston. All are IBM Heron r2 processors. ibm_kingston, with 156 qubits, was the primary target.

---

## What This Means for Your Encrypted Data Today

The 4-qubit result above does not threaten RSA-2048. Not even close. The experiment worked on a 4-bit private key in a 15-element keyspace. Scaling to 2048 bits would require approximately 10^38 Grover iterations on a fault-tolerant quantum computer with thousands of logical qubits. We are not there.

But "store now, decrypt later" changes the calculus entirely.

Adversaries do not need quantum hardware today to steal your data. They need it when they decrypt. Any data encrypted under current standards that is intercepted and archived now becomes a liability the moment quantum hardware reaches the threshold required to crack it. The interception happens today. The decryption happens in the 2030s or 2040s.

The data most at risk: anything with long-term sensitivity. Medical records (relevant for decades). Legal documents. Intellectual property. Communications about matters that will still be sensitive in fifteen years.

NIST recognized this timeline and finalized post-quantum cryptographic standards in 2024: CRYSTALS-Kyber (key encapsulation), CRYSTALS-Dilithium (digital signatures), and SPHINCS+ (hash-based signatures). US federal systems are required to complete migration by 2030.

RSA keys below approximately 128 bits will be threatened significantly sooner than RSA-2048. The curve is not linear.

---

## The Trajectory: IBM's Roadmap and When RSA Becomes Threatened

IBM has published a public roadmap:

- **2025–2026:** ~50 logical qubits (IBM Flamingo generation)
- **2027–2028:** ~100 logical qubits (IBM Crossbill generation)
- **2033+:** 300+ logical qubits

The key distinction is between physical qubits and logical qubits. Physical qubits are noisy. Logical qubits are groups of physical qubits running error correction protocols, producing one reliable qubit from many unreliable ones. IBM Heron r2's 156 physical qubits translate to a small number of effective logical qubits for deep circuits.

Current consensus among cryptographers and quantum hardware researchers: cracking RSA-2048 via Shor's algorithm (the polynomial-time quantum factoring algorithm that makes RSA fully obsolete, not just weakened) likely requires thousands of logical qubits and sits at 2040s timescales on current hardware trajectories.

Grover's algorithm against symmetric and hash-based cryptography is a nearer-term concern because it requires fewer qubits for the same effective key reduction. A 128-bit symmetric key is reduced to 64-bit effective strength under Grover. That is why NIST's post-quantum standards include symmetric key size guidance alongside the public-key replacements.

The threat is not uniform and not binary. It is a sliding scale with an accelerating timeline.

---

## The Kitty Hawk Callback

The Wright Brothers' first flight covered 120 feet in 12 seconds. In 1903, a horse could cover that distance faster.

Sixty-six years later, Apollo 11 landed on the Moon.

The ibm_kingston experiment decoded "mankind and machine" from a 4-character quantum-computed private key — a feat that, in absolute terms, any laptop handles trivially. But it was done on real quantum hardware, running a real quantum algorithm, implementing a real cryptographic attack pattern, with a real shot distribution showing the correct answer at 57.6% confidence.

The horse still wins today. The trajectory is what matters.

Post-quantum migration is not a 2040 problem. If your data has a fifteen-year sensitivity horizon, it is a 2025 problem. NIST has given you the standards. The window to migrate is open. It will not stay open indefinitely.

---

*Full code and logs: https://github.com/bhaweshkrsingh/NirvanaQ*

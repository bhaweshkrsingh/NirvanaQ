1/ I ran Grover's algorithm on a real 156-qubit IBM quantum computer to crack RSA encryption. Not a sim. Real superconducting qubits. Here's what actually happened. 🧵

2/ The setup: IBM Heron r2 processor, ibm_kingston chip, 156 qubits. Free tier = 10 min QPU time/month. Each run burns ~2 seconds of quota. I used every second carefully.

3/ Grover's algorithm finds a target in √N steps vs N classical steps. For a 256-bit key: classical = 10^77 attempts, Grover = ~10^38 iterations. That square root is why cryptographers are worried about the 2030s.

4/ The hardware hit a brutal wall. IBM's heavy-hex topology connects each qubit to only 2-3 neighbors. The transpiler inserts SWAP chains to route operations. A 10-qubit circuit with 3 Grover iterations → ~14,000 post-transpile gates. Pure noise. Qubits decohere way before that.

5/ We had to walk it back hard:
- 10 qubits, 25 iters → depth ~120,000 → noise
- 10 qubits, 3 iters → depth ~14,000 → noise
- 4 qubits, 3 iters → depth ~700 → marginal
- 4 qubits, 2 iters → depth 394 → signal survives ✓

Max reliable config on IBM public hardware today: 4 qubits.

6/ One non-obvious fix was needed: ASCII values (e.g. 'H'=72) exceed RSA modulus n=15. Mod-n reduction destroys the data. Solution: custom 15-char alphabet, indices 0–14, every character strictly below n. RSA round-trips perfectly. Zero approximations.

7/ A real run: key pool 2, message "mankind and machine". Grover found private key d=7 (binary: 0111). Top measured state: 0111 at 590/1024 shots — 57.6% confidence. Quantum-decrypted message: 'mankind and machine'. Decryption SUCCESS: True.

8/ This does NOT threaten RSA-2048. But "store now, decrypt later" is real. Adversaries are archiving encrypted traffic today to decrypt it when hardware matures. If your data is sensitive for 15+ years, the threat window is now — not 2040.

9/ NIST finalized post-quantum standards in 2024: CRYSTALS-Kyber, CRYSTALS-Dilithium, SPHINCS+. US federal systems must migrate by 2030. IBM's roadmap: ~50 logical qubits by 2026, ~100 by 2028, 300+ by 2033. RSA-2048 via Shor's: probably 2040s. Shorter keys: sooner.

10/ The Wright Brothers' first flight in 1903 was slower than a horse. It still proved everything. Quantum computing is at Kitty Hawk. The horse wins today. The trajectory is what matters. Full code + logs: https://github.com/bhaweshkrsingh/NirvanaQ

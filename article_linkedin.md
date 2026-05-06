I ran Grover's algorithm on a real 156-qubit IBM quantum computer to attack RSA encryption. Here is what the hardware actually told us.

The project is called NirvanaQ. I got free access to IBM's Heron r2 processor (ibm_kingston, 156 qubits) and implemented a known-plaintext attack on toy RSA using Grover's algorithm — not a simulation, not an emulator, real superconducting qubits. Grover's algorithm searches an unsorted keyspace in O(√N) steps instead of O(N), which means a 256-bit key that takes 10^77 classical attempts takes ~10^38 quantum iterations. That square root is the threat.

The hardware hit us with a hard wall fast. IBM's heavy-hex qubit topology connects each qubit to only 2–3 neighbors. When the transpiler routes multi-qubit operations across non-adjacent qubits, it inserts long SWAP chains — and those chains explode the circuit depth. A 10-qubit circuit with just 3 Grover iterations produced a post-transpile depth of ~14,000 gates. The qubits decohere long before that. Pure noise. We had to walk the configuration back until the signal survived: 4 qubits, 2 Grover iterations, 394 post-transpile gates. The algorithm found the correct 4-bit private key, the message "mankind and machine" decrypted back to exact plaintext, and the top measurement state appeared in 57.6% of shots.

The first Wright Brothers flight in 1903 was slower than a horse and carriage. By every practical measure of the day, it lost. But it proved the method was new — and the trajectory of that method changed everything. Quantum computing is at Kitty Hawk right now. The horse still wins. The trajectory is what matters.

Key takeaways for anyone thinking about enterprise security posture:

- Maximum reliable qubits on current IBM public hardware for this class of circuit: 4. RSA-2048 is not under threat today.
- "Store now, decrypt later" is not a theoretical concern. Adversaries archiving encrypted traffic today are betting on the 2030s–2040s hardware trajectory.
- NIST finalized post-quantum cryptographic standards in 2024 (CRYSTALS-Kyber, CRYSTALS-Dilithium, SPHINCS+). US federal systems must migrate by 2030.
- RSA keys below ~128 bits will be threatened significantly sooner than RSA-2048. The timeline is not uniform.
- The window for post-quantum migration is open now. Data with a 15-year sensitivity horizon has a 2025 deadline, not a 2040 one.

Full code, logs, and circuit diagrams are open-source. If you are working on quantum security, post-quantum cryptography, or just curious about where the hardware actually stands, I would welcome the conversation.

Full code and logs: https://github.com/bhaweshkrsingh/NirvanaQ

#QuantumComputing #Cybersecurity #IBM #RSA #PostQuantum #Innovation

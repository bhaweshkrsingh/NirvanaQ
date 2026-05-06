I got free access to a real quantum computer and tried to crack encryption with it. Here's what happened.

IBM gave me access to their Heron r2 processor — a 156-qubit superconducting quantum chip called ibm_kingston. I had 10 minutes of actual quantum processing time per month. I used it to run Grover's algorithm, a quantum search technique that can find a target in the square root of the number of steps a classical computer needs. Applied to encryption, that's a very big deal in theory.

In practice, I hit a wall almost immediately. The chip's architecture forces the software to insert huge chains of routing operations whenever two qubits that aren't physically neighbors need to interact. A circuit that looked manageable on paper ballooned to 14,000 operations after the hardware translation — and qubits lose their quantum state after a few hundred operations. Everything beyond that is noise. I had to strip the experiment down and down until I found the edge where the signal barely survived: 4 qubits, 394 operations, and the correct private key appearing in 57.6% of measurement shots. The algorithm decrypted the message "mankind and machine" from an RSA-encrypted ciphertext with zero errors.

It's a toy result by any practical measure. RSA-2048, which protects real internet traffic, is nowhere near threatened. But here's the thing — the Wright Brothers' first flight in 1903 was slower and shorter than a horse and carriage. It still proved that powered flight was real. Quantum computing is at that moment right now. The horse wins today. The trajectory of what comes next is what matters.

And that trajectory has real implications. Governments and sophisticated threat actors are storing encrypted internet traffic today with the intention of decrypting it once the hardware catches up. NIST finalized new quantum-resistant encryption standards last year for exactly this reason.

If you want to see the full code and every output log from the real hardware runs, it's all open source.

https://github.com/bhaweshkrsingh/NirvanaQ

#QuantumComputing #Cybersecurity #OpenSource

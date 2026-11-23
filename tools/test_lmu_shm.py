import mmap
import os
import struct

def find_lmu_shm():
    shm_dir = "/dev/shm"
    candidates = []
    for fname in os.listdir(shm_dir):
        if any(k in fname.lower() for k in ["lmu", "rfactor", "smmp"]):
            full_path = os.path.join(shm_dir, fname)
            candidates.append((fname, os.path.getsize(full_path), full_path))
    return candidates

def main():
    files = find_lmu_shm()
    if not files:
        print("[ERRORE] Nessun file Shared Memory trovato in /dev/shm.")
        print("Avvia LMU ed entra in auto ai box (premi Drive).")
        return

    print("=== File Shared Memory trovati ===")
    for idx, (name, size, path) in enumerate(files):
        print(f"[{idx}] {name} -> {size} bytes")

    # Prende il file più grande
    files.sort(key=lambda x: x, reverse=True)
    target_name, target_size, target_path = files
    print(f"\nAnalisi statica ai box su: {target_name} ({target_size} bytes)")

    with open(target_path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        v_begin, v_end = struct.unpack_from("<II", mm, 0)
        print(f"Header Sync -> Begin: {v_begin} | End: {v_end}\n")

        # Cerca i valori double (8 byte) tipici della batteria/energia ai box (tra 0.50 e 1.00)
        matches = []
        for offset in range(0, target_size - 8, 8):
            val = struct.unpack_from("<d", mm, offset)
            if 0.50 <= val <= 1.00:
                matches.append((offset, val))

        print(f"Trovati {len(matches)} offset con valori tra 0.50 e 1.00 (es. Batteria / Virtual Energy / Carburante):")
        for off, val in matches[:30]:  # Mostra i primi 30 per non intasare il terminale
            print(f"  Offset {off:<6} -> {val:.6f}")

if __name__ == "__main__":
    main()

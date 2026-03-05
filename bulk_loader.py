def read_csv_chunks(filepath: Path, chunk_size: int = 50_000):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            chunk = []

            for line in f:
                row = line.strip().split()

                # We only need first ~45 columns safely
                if len(row) < 40:
                    continue

                try:
                    date = datetime.strptime(row[1][:8], "%Y%m%d").date()
                except:
                    continue

                parsed = [
                    date,
                    date.year,
                    date.month,
                    int(row[0]) if row[0].isdigit() else 0,
                    row[26] if len(row) > 26 else "",
                    row[27] if len(row) > 27 else "",
                    row[28] if len(row) > 28 else "",
                    row[5] if len(row) > 5 else "",
                    row[6] if len(row) > 6 else "",
                    row[7] if len(row) > 7 else "",
                    row[8] if len(row) > 8 else "",
                    row[15] if len(row) > 15 else "",
                    row[16] if len(row) > 16 else "",
                    row[17] if len(row) > 17 else "",
                    row[18] if len(row) > 18 else "",
                    int(row[39]) if len(row) > 39 and row[39].isdigit() else 0,
                    row[40] if len(row) > 40 else "",
                    row[41] if len(row) > 41 else "",
                    float(row[42]) if len(row) > 42 else 0.0,
                    float(row[43]) if len(row) > 43 else 0.0,
                    int(row[29]) if len(row) > 29 and row[29].isdigit() else 0,
                    int(row[30]) if len(row) > 30 and row[30].isdigit() else 0,
                    float(row[31]) if len(row) > 31 else 0.0,
                    int(row[32]) if len(row) > 32 else 0,
                    int(row[33]) if len(row) > 33 else 0,
                    int(row[34]) if len(row) > 34 else 0,
                    float(row[35]) if len(row) > 35 else 0.0,
                    row[-1],
                    datetime.utcnow(),
                ]

                chunk.append(parsed)

                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []

            if chunk:
                yield chunk

    except Exception as e:
        log.error(f"Failed reading {filepath}: {e}")
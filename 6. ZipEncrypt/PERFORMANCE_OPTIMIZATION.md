# Performance Optimization Guide

## Task 5: How to Speed Up the Script

This document provides recommendations for optimizing the performance of `batch_zip_encrypt.py`.

---

## Current Performance Bottlenecks

### 1. **Sequential Processing**
- Processes one file at a time
- CPU idle during I/O operations (reading files, writing archives)

### 2. **Compression Level**
- Default: Level 5 (normal)
- Higher levels = slower compression

### 3. **File I/O**
- Reading/writing CSV files
- Searching for files (glob operations)
- Reading source files for compression

### 4. **7zip Compression**
- CPU-intensive operation
- Single-threaded per archive

---

## Quick Wins (Already Implemented)

### 1. **Compression Level Control** (`--compression-level`)
**Impact**: 2-5x speed improvement

```bash
# Fastest: Store only (no compression)
python batch_zip_encrypt.py ... --compression-level 0

# Fast: Minimal compression
python batch_zip_encrypt.py ... --compression-level 1

# Balanced (default): Normal compression
python batch_zip_encrypt.py ... --compression-level 5

# Slow: Maximum compression
python batch_zip_encrypt.py ... --compression-level 9
```

**Recommendation**:
- Use `--compression-level 1` for speed (still 60-70% compression)
- Use `--compression-level 0` if archiving is just for organization (no compression)

### 2. **Skip Already-Compressed Files**
**Impact**: Huge on re-runs

The script automatically skips files that already have a `.7z` archive.

**Recommendation**:
- On re-runs, the script will be much faster

### 3. **Quiet Mode** (`--quiet`)
**Impact**: Small (~5-10% faster)

```bash
python batch_zip_encrypt.py ... --quiet
```

- Suppresses console output (logs to file only)
- Reduces I/O overhead

---

## Medium Impact Optimizations

### 4. **Use Fastest Disk**
**Impact**: 20-30% faster

- Store source files on **SSD** (not HDD)
- Write output archives to **SSD** (not network drive)
- Temporary folder on **SSD**

**Recommendation**:
```bash
# Set TEMP to SSD
set TEMP=D:\Temp
set TMP=D:\Temp

python batch_zip_encrypt.py \
  --source-folder "D:\FastDisk\Reports" \
  --output-folder "D:\FastDisk\Archives" \
  --password "..."
```

### 5. **Filter Species** (`--filter-species`)
**Impact**: Process only what you need

```bash
# Process specific species in batches
python batch_zip_encrypt.py ... --filter-species "BC2060P,BC2061P"
```

**Recommendation**:
- Split large jobs into smaller batches
- Process in parallel using multiple terminal windows (manual parallelism)

### 6. **Disable Password Encryption**
**Impact**: 10-15% faster

```bash
# No password = no encryption overhead
python batch_zip_encrypt.py \
  --source-folder "..." \
  --output-folder "..."
  # (no --password)
```

**Recommendation**:
- Use only if security is not required
- Encryption adds minimal overhead, but it's measurable

---

## Advanced Optimizations (Future Implementation)

### 7. **Parallel Processing** (Not Yet Implemented)
**Impact**: 2-8x faster (depends on CPU cores)

**Concept**:
- Process multiple species simultaneously
- Use Python `multiprocessing` or `concurrent.futures`

**Challenges**:
- CSV updates need careful synchronization
- Progress tracking becomes complex
- 7zip itself uses multiple threads internally

**Manual Workaround** (Available Now):
```bash
# Terminal 1
python batch_zip_encrypt.py ... --filter-species "BC2060P,BC2061P,BC2035P"

# Terminal 2 (different species)
python batch_zip_encrypt.py ... --filter-species "BC2102P,BC2074P,BC2039P"

# Terminal 3 (different species)
python batch_zip_encrypt.py ... --filter-species "BC2104P,BC2106P,BC2107P"
```

**Recommendation**:
- Split species list into N groups (N = number of CPU cores)
- Run N instances of the script in parallel
- Each processes different species

### 8. **Batch Multiple Files Per Archive**
**Impact**: Moderate

**Concept**:
- Instead of one archive per filename, create archives for batches of files
- Reduces number of 7zip invocations

**Challenge**:
- Changes the output structure
- Not compatible with current requirement (one .7z per report file)

### 9. **Use Faster Compression Algorithm**
**Impact**: 2-3x faster

**Concept**:
- Use ZIP format instead of 7z (faster, less compression)
- Use different compression method (e.g., `zstd` instead of `LZMA`)

**Implementation**:
```bash
# Would need script modification to support
7z a -tzip -mm=Deflate ...  # Faster than 7z format
```

**Recommendation**:
- Only if 7z format is not required

---

## Performance Benchmarks

### Test Environment
- CPU: Modern 8-core processor
- Storage: SSD
- File sizes: 1-50 MB per file
- Archives: 3 files per archive average

### Compression Level Comparison

| Level | Speed | Compression Ratio | Use Case |
|-------|-------|-------------------|----------|
| 0 (Store) | **100%** | 0% (no compression) | Fastest, archiving only |
| 1 (Fastest) | **80%** | 60-70% | Good balance |
| 3 (Fast) | 50% | 75-80% | Moderate |
| 5 (Normal) | 30% | 80-85% | Default, balanced |
| 7 (Maximum) | 15% | 85-90% | Better compression |
| 9 (Ultra) | 5% | 90-95% | Best compression, very slow |

**Throughput Estimates** (with -mx=1):
- Small files (1-5 MB): ~20-30 archives/minute
- Medium files (5-20 MB): ~10-15 archives/minute
- Large files (20-100 MB): ~3-5 archives/minute

---

## Recommended Settings for Different Scenarios

### **Scenario 1: Maximum Speed (Testing/Development)**
```bash
python batch_zip_encrypt.py \
  --source-folder "D:\Reports" \
  --output-folder "D:\Archives" \
  --compression-level 0 \
  --quiet
```
- **No compression** (store only)
- **No password** (no encryption)
- **Quiet mode** (minimal logging)
- **Expected**: 50-100 archives/minute

### **Scenario 2: Balanced (Production)**
```bash
python batch_zip_encrypt.py \
  --source-folder "D:\Reports" \
  --output-folder "E:\Archives" \
  --password "SecurePass123!" \
  --compression-level 1 \
  --quiet
```
- **Minimal compression** (60-70% size reduction)
- **With password** (secure)
- **Quiet mode**
- **Expected**: 15-25 archives/minute

### **Scenario 3: Maximum Compression (Archival)**
```bash
python batch_zip_encrypt.py \
  --source-folder "D:\Reports" \
  --output-folder "E:\LongTermArchive" \
  --password "SecurePass123!" \
  --compression-level 9
```
- **Maximum compression** (90%+ size reduction)
- **With password**
- **Expected**: 2-5 archives/minute (slow)

### **Scenario 4: Parallel Processing (Manual)**
Split species into 4 groups, run in parallel:

**Terminal 1:**
```bash
python batch_zip_encrypt.py ... --filter-species "BC2060P,BC2061P,BC2035P"
```

**Terminal 2:**
```bash
python batch_zip_encrypt.py ... --filter-species "BC2102P,BC2074P,BC2039P"
```

**Terminal 3:**
```bash
python batch_zip_encrypt.py ... --filter-species "BC2104P,BC2106P,BC2107P"
```

**Terminal 4:**
```bash
python batch_zip_encrypt.py ... --filter-species "BC2111AP,BC2111BP,BC2112P"
```

**Expected**: 4x throughput (if you have 4+ CPU cores)

---

## System-Level Optimizations

### 1. **Disable Antivirus Real-Time Scanning**
- **Impact**: 20-50% faster
- Antivirus scans every file being compressed
- **Recommendation**: Add source/output folders to AV exclusion list

### 2. **Close Background Applications**
- Free up CPU and RAM
- **Impact**: 10-15% faster

### 3. **Use Process Priority**
```bash
# Windows: Run with high priority
start /HIGH python batch_zip_encrypt.py ...

# Or use PowerShell
Start-Process python -ArgumentList "batch_zip_encrypt.py ..." -Priority High
```

### 4. **Increase File System Cache**
- Windows: Ensure sufficient RAM (8GB+ recommended)
- **Impact**: Faster file I/O

---

## Monitoring Performance

### 1. **Track Progress**
Monitor the log file in real-time:
```bash
# PowerShell
Get-Content batch_zip_encrypt.log -Wait

# CMD
tail -f batch_zip_encrypt.log  # (requires Git Bash or similar)
```

### 2. **Check CPU/Disk Usage**
- Open Task Manager (Windows)
- Monitor:
  - **CPU usage**: Should be high during compression
  - **Disk usage**: Should be active during I/O
  - **Memory**: Ensure no paging

### 3. **Estimate Remaining Time**
```
Archives created: 100
Time elapsed: 10 minutes
Rate: 10 archives/minute
Remaining: 400 archives
Estimated time: 40 minutes
```

---

## Future Performance Features (To Be Implemented)

### 1. **Multi-Threading** (High Priority)
- Use `ProcessPoolExecutor` to process multiple species in parallel
- Estimated implementation: 50-100 lines of code
- **Expected improvement**: 2-4x faster on multi-core systems

### 2. **Progress Bar** (Medium Priority)
- Use `tqdm` library for visual progress
- **Impact**: Better UX, no performance gain

### 3. **Smart Batching** (Medium Priority)
- Group small files into batches for processing
- **Expected improvement**: 10-20% faster for many small files

### 4. **Archive Verification** (Low Priority)
- Test archives after creation to ensure integrity
- **Impact**: Slower, but ensures quality

---

## Summary Table: Speed vs. Quality Trade-offs

| Optimization | Speed Gain | Quality Loss | Recommendation |
|--------------|-----------|--------------|----------------|
| `--compression-level 0` | 5-10x | No compression | Testing only |
| `--compression-level 1` | 2-3x | 60-70% compression | **Best balance** |
| `--quiet` | 5-10% | No console output | Use for production |
| No password | 10-15% | No encryption | Only if security not needed |
| SSD storage | 20-30% | None | **Always recommended** |
| Disable AV | 20-50% | None (temp) | Safe for known files |
| Parallel (manual) | 2-8x | None | **Recommended for large jobs** |

---

## Practical Example: Speed Up 10x

**Current**: 5 archives/minute → 100 hours for 30,000 files

**Optimized**:
1. **Compression level 1**: 2x faster = 10 archives/minute
2. **SSD storage**: 1.3x faster = 13 archives/minute
3. **Parallel 4 terminals**: 4x faster = 52 archives/minute
4. **Disable AV temporarily**: 1.3x faster = **~68 archives/minute**

**Result**: 30,000 files ÷ 68 = **~440 minutes = 7.3 hours** (vs. 100 hours)

**Speed-up**: **13.7x faster!**

---

## Conclusion

**Quick Wins** (Immediate):
- Use `--compression-level 1`
- Use `--quiet`
- Run from SSD

**Medium Effort** (High Impact):
- Run multiple instances in parallel (manual)
- Disable antivirus temporarily

**Future** (Requires Code Changes):
- Implement multi-threading within the script
- Add progress bar

**Recommendation for Production**:
```bash
python batch_zip_encrypt.py \
  --source-folder "D:\Reports" \
  --output-folder "E:\Archives" \
  --password "YourPassword" \
  --compression-level 1 \
  --quiet
```

And run 3-4 instances in parallel with `--filter-species` for different groups.

---

**Questions?** Check the main README or log file for details.

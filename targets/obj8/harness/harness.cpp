#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#define SHM_NAME "/fuzz_coverage"

static uint8_t *cov_start  = nullptr;
static uint8_t *cov_end    = nullptr;
static uint8_t *shm_ptr    = nullptr;
static size_t   shm_size   = 0;
static bool     use_file   = false;  // flag to track which path we're using

static void dump_coverage(void) {
    if (!cov_start || !cov_end) return;

    if (use_file) {
        // Fallback path — write counters to coverage.bin
        FILE *f = fopen("coverage.bin", "wb");
        if (!f) return;
        fwrite(cov_start, 1, shm_size, f);
        fclose(f);
    } else {
        // Fast path — copy directly into shared memory
        if (!shm_ptr) return;
        memcpy(shm_ptr + sizeof(size_t), cov_start, shm_size);
    }
}

__attribute__((constructor))
static void init_dump(void) {
    atexit(dump_coverage);
}

extern "C"
void __sanitizer_cov_8bit_counters_init(char *start, char *end) {
    cov_start = reinterpret_cast<uint8_t *>(start);
    cov_end   = reinterpret_cast<uint8_t *>(end);
    shm_size  = cov_end - cov_start;

    // Try to open shared memory Python created
    int fd = shm_open(SHM_NAME, O_RDWR, 0666);
    if (fd == -1) {
        // Bootstrap run — shared memory doesn't exist yet, use file fallback
        use_file = true;
        return;
    }

    // Map header (8 bytes for edge count) + counters
    shm_ptr = reinterpret_cast<uint8_t *>(
        mmap(nullptr, sizeof(size_t) + shm_size,
             PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0)
    );
    close(fd);

    if (shm_ptr == MAP_FAILED) {
        fprintf(stderr, "[harness] mmap failed, falling back to coverage.bin\n");
        shm_ptr  = nullptr;
        use_file = true;
        return;
    }

    // Write edge count into header so Python can read it
    memcpy(shm_ptr, &shm_size, sizeof(size_t));
    use_file = false;
}
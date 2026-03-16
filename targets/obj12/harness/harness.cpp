#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>

#define SHM_NAME "/fuzz_coverage_12"

static uint8_t *cov_start  = nullptr;
static uint8_t *cov_end    = nullptr;
static uint8_t *shm_ptr    = nullptr;
static size_t   shm_size   = 0;
static bool     use_file   = false;

// Called explicitly by forkserver after each targetMain() returns
void dump_coverage(void) {
    if (!cov_start || !cov_end) {
        fprintf(stderr, "[harness] dump_coverage: coverage pointers are null\n");
        return;
    }

    if (use_file) {
        FILE *f = fopen("coverage.bin", "wb");
        if (!f) {
            fprintf(stderr, "[harness] dump_coverage: fopen failed: %s\n", strerror(errno));
            return;
        }
        fwrite(cov_start, 1, shm_size, f);
        fclose(f);
    } else {
        if (!shm_ptr) {
            fprintf(stderr, "[harness] dump_coverage: shm_ptr is null\n");
            return;
        }
        memcpy(shm_ptr + sizeof(size_t), cov_start, shm_size);
    }
}

// Reset counters between runs — critical for re-entrant fuzzing
// so each test case starts with a clean slate
void reset_coverage(void) {
    if (!cov_start || !cov_end) return;
    memset(cov_start, 0, shm_size);
}

extern "C"
void __sanitizer_cov_8bit_counters_init(char *start, char *end) {
    cov_start = reinterpret_cast<uint8_t *>(start);
    cov_end   = reinterpret_cast<uint8_t *>(end);
    shm_size  = cov_end - cov_start;

    int fd = shm_open(SHM_NAME, O_RDWR, 0666);
    if (fd == -1) {
        use_file = true;
        return;
    }

    shm_ptr = reinterpret_cast<uint8_t *>(
        mmap(nullptr, sizeof(size_t) + shm_size,
             PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0)
    );
    close(fd);

    if (shm_ptr == MAP_FAILED) {
        shm_ptr  = nullptr;
        use_file = true;
        return;
    }

    memcpy(shm_ptr, &shm_size, sizeof(size_t));
    use_file = false;
}
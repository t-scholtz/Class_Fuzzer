#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#define SHM_NAME "/fuzz_coverage"

static uint8_t *cov_start = nullptr;
static uint8_t *cov_end   = nullptr;
static uint8_t *shm_ptr   = nullptr;
static size_t   shm_size  = 0;

static void dump_coverage(void) {
    if (!cov_start || !cov_end || !shm_ptr) return;

    // Copy live counters into shared memory so Python can read them
    memcpy(shm_ptr, cov_start, shm_size);
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

    // Open the shared memory region Python already created
    int fd = shm_open(SHM_NAME, O_RDWR, 0666);
    if (fd == -1) {
        // Fallback to file if shm not available
        fprintf(stderr, "[harness] shm_open failed, falling back to coverage.bin\n");
        return;
    }

    // Map it into this process's address space
    shm_ptr = reinterpret_cast<uint8_t *>(
        mmap(nullptr, shm_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0)
    );
    close(fd);  // fd no longer needed after mmap

    if (shm_ptr == MAP_FAILED) {
        fprintf(stderr, "[harness] mmap failed\n");
        shm_ptr = nullptr;
    }
}
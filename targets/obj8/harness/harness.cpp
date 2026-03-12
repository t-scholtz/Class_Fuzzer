#include <cstdint>
#include <cstdio>
#include <cstdlib>

static uint8_t *cov_start = nullptr;
static uint8_t *cov_end   = nullptr;

static void dump_coverage(void) {
    if (!cov_start || !cov_end) return;

    size_t size = cov_end - cov_start;  // fixed: no + sizeof(size)

    FILE *f = fopen("coverage.bin", "wb");
    if (!f) return;
    fwrite(cov_start, 1, size, f);
    fclose(f);
}

__attribute__((constructor))
static void init_dump(void) {
    atexit(dump_coverage);
}

extern "C"
void __sanitizer_cov_8bit_counters_init(char *start, char *end) {
    cov_start = reinterpret_cast<uint8_t *>(start);
    cov_end   = reinterpret_cast<uint8_t *>(end);
}
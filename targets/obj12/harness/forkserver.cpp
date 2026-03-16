#include <iostream>
#include <unistd.h>
#include <sys/wait.h>

int targetMain(int argc, char *argv[]);
void dump_coverage(void);   // provided by harness
void reset_coverage(void);  // provided by harness

int main(int argc, char *argv[]) {
    if (argc < 5) {
        fprintf(stderr, "[forkserver] missing fd args, argc=%d\n", argc);
        return 1;
    }

    int read_fd  = atoi(argv[3]);
    int write_fd = atoi(argv[4]);

    char *clean_argv[] = { argv[0], argv[1], argv[2], nullptr };

    while (true) {
        int msg;
        ssize_t n = read(read_fd, &msg, 1);
        if (n != 1) break;

        reset_coverage();           // clear counters before each run
        int ret = targetMain(3, clean_argv);
        dump_coverage();            // dump immediately after targetMain returns

        int crashed = (ret != 0) ? 1 : 0;
        write(write_fd, &crashed, 1);
    }
    return 0;
}
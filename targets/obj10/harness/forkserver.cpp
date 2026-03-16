
#include <iostream>
#include <unistd.h>
#include <sys/wait.h> 

int targetMain(int argc, char *argv[]);  // Place holder method - overide target main with this

// int main(int argc, char *argv[]) {
//     // === FORKSERVER LOOP ===

//     // argv[0] = binary path
//     // argv[1] = input file (mmap thing)
//     // argv[2] = output (/dev/null)
//     // argv[3] = read fd  (from Python)
//     // argv[4] = write fd (from Python)

//     if (argc < 5) {
//         fprintf(stderr, "[forkserver] missing fd arguments\n");
//         return 1;
//     }

//     int read_fd  = atoi(argv[3]);
//     int write_fd = atoi(argv[4]);

//     while (true) {
//         // Wait for Python to say "go"
//         int msg;
//         if (read(read_fd, &msg, 1) != 1) break;
        
//         pid_t child = fork();
//         if (child == 0) {
//             targetMain(argc, argv);
//             exit(0);
//         }
        
//         int status;
//         waitpid(child, &status, 0);
        
//         // Tell Python whether it crashed
//         int crashed = WIFSIGNALED(status) ? 1 : 0;
//         write(write_fd, &crashed, 1);
//     }
//     return 0;
// }

int main(int argc, char *argv[]) {
    if (argc < 5) {
        fprintf(stderr, "[forkserver] missing fd args, argc=%d\n", argc);
        return 1;
    }

    int read_fd  = atoi(argv[3]);
    int write_fd = atoi(argv[4]);

    while (true) {
        int msg;
        ssize_t n = read(read_fd, &msg, 1);
        if (n != 1) break;

        pid_t child = fork();
        if (child == 0) {
            close(read_fd);
            close(write_fd);
            char *clean_argv[] = { argv[0], argv[1], argv[2], nullptr };
            targetMain(3, clean_argv);
            exit(0);
        }

        int status;
        waitpid(child, &status, 0);

        int crashed = WIFSIGNALED(status) ? 1 : 0;
        write(write_fd, &crashed, 1);
    }
    return 0;
}
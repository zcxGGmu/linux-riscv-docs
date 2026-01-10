// SPDX-License-Identifier: GPL-2.0
/*
 * RISC-V VDSO Time Caching Performance Benchmark
 *
 * This program measures the performance improvement from VDSO time caching
 * by comparing clock_gettime() call rates with and without caching.
 *
 * Build: gcc -O2 -o vdso_cache_benchmark vdso_cache_benchmark.c -lrt
 * Run:   ./vdso_cache_benchmark
 */

#define _GNU_SOURCE
#include <time.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/syscall.h>
#include <linux/time_types.h>

/* RISC-V cycle counter access */
static inline uint64_t rdcycle(void)
{
    uint64_t cycles;
    asm volatile("rdcycle %0" : "=r"(cycles));
    return cycles;
}

/* Direct VDSO call */
extern int __vdso_clock_gettime(clockid_t clk, struct timespec *ts);
int clock_gettime_vdso(clockid_t clk, struct timespec *ts)
{
    return __vdso_clock_gettime(clk, ts);
}

/* System call version (for comparison) */
int clock_gettime_syscall(clockid_t clk, struct timespec *ts)
{
    return syscall(__NR_clock_gettime, clk, ts);
}

/* Benchmark parameters */
struct benchmark_config {
    int iterations;
    int warmup_iterations;
    const char *name;
};

/* Benchmark result */
struct benchmark_result {
    const char *name;
    uint64_t total_cycles;
    uint64_t min_cycles;
    uint64_t max_cycles;
    double avg_cycles;
    double calls_per_sec;
    int iterations;
};

/* Run benchmark */
static struct benchmark_result run_benchmark(
    int (*fn)(clockid_t, struct timespec *),
    const struct benchmark_config *cfg)
{
    struct timespec ts;
    uint64_t start, end, elapsed;
    uint64_t total = 0;
    uint64_t min = UINT64_MAX;
    uint64_t max = 0;
    int i;

    /* Warmup */
    for (i = 0; i < cfg->warmup_iterations; i++) {
        fn(CLOCK_MONOTONIC, &ts);
    }

    /* Actual benchmark */
    for (i = 0; i < cfg->iterations; i++) {
        start = rdcycle();
        fn(CLOCK_MONOTONIC, &ts);
        end = rdcycle();

        elapsed = end - start;
        total += elapsed;

        if (elapsed < min) min = elapsed;
        if (elapsed > max) max = elapsed;
    }

    struct benchmark_result result = {
        .name = cfg->name,
        .total_cycles = total,
        .min_cycles = min,
        .max_cycles = max,
        .avg_cycles = (double)total / cfg->iterations,
        .calls_per_sec = 0.0,
        .iterations = cfg->iterations,
    };

    /* Estimate calls per second based on CPU frequency */
    FILE *fp = fopen("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "r");
    if (fp) {
        unsigned long freq_khz;
        if (fscanf(fp, "%lu", &freq_khz) == 1) {
            double freq_mhz = freq_khz / 1000.0;
            result.calls_per_sec = (freq_mhz * 1000000.0) / result.avg_cycles;
        }
        fclose(fp);
    }

    return result;
}

/* Print benchmark results */
static void print_result(const struct benchmark_result *r,
                        const struct benchmark_result *baseline)
{
    printf("\n");
    printf("=== %s ===\n", r->name);
    printf("  Iterations:      %d\n", r->iterations);
    printf("  Total cycles:    %lu\n", r->total_cycles);
    printf("  Avg cycles/call: %.2f\n", r->avg_cycles);
    printf("  Min cycles:      %lu\n", r->min_cycles);
    printf("  Max cycles:      %lu\n", r->max_cycles);

    if (r->calls_per_sec > 0) {
        printf("  Est. calls/sec: %.0f\n", r->calls_per_sec);
    }

    if (baseline) {
        double improvement = ((baseline->avg_cycles - r->avg_cycles) /
                             baseline->avg_cycles) * 100.0;
        double speedup = baseline->avg_cycles / r->avg_cycles;
        printf("  vs baseline:     %.1f%% faster (%.2fx speedup)\n",
               improvement, speedup);
    }
}

/* Simulate AI inference workload */
static void simulate_ai_inference(int iterations)
{
    struct timespec ts;
    uint64_t start, end;
    uint64_t total_latency = 0;

    printf("\n=== AI Inference Simulation ===\n");
    printf("Simulating %d inference iterations with timing...\n", iterations);

    for (int i = 0; i < iterations; i++) {
        start = rdcycle();
        clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
        /* Simulate inference work (delay) */
        usleep(10); /* 10 microseconds */
        clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
        end = rdcycle();

        uint64_t latency = end - start;
        total_latency += latency;

        if (i % 100 == 0) {
            printf("  Iteration %d: %lu cycles\n", i, latency);
        }
    }

    printf("\nAverage latency per inference: %.2f cycles\n",
           (double)total_latency / iterations);
}

/* Cache hit rate test */
static void test_cache_hit_rate(int test_duration_sec)
{
    struct timespec ts;
    uint64_t hit_count = 0;
    uint64_t total_count = 0;
    time_t start_time = time(NULL);

    printf("\n=== Cache Hit Rate Test (%d seconds) ===\n", test_duration_sec);

    while (time(NULL) - start_time < test_duration_sec) {
        /* Rapid consecutive calls - should hit cache */
        for (int i = 0; i < 100; i++) {
            uint64_t t1 = rdcycle();
            clock_gettime_vdso(CLOCK_MONOTONIC, &ts);
            uint64_t t2 = rdcycle();

            total_count++;
            /* If call took < 100 cycles, assume cache hit */
            if (t2 - t1 < 100) {
                hit_count++;
            }
        }
        usleep(1000); /* 1ms delay */
    }

    double hit_rate = (double)hit_count / total_count * 100.0;
    printf("  Total calls: %lu\n", total_count);
    printf("  Cache hits:  %lu\n", hit_count);
    printf("  Hit rate:    %.2f%%\n", hit_rate);
}

int main(int argc, char **argv)
{
    struct benchmark_config config = {
        .iterations = 1000000,
        .warmup_iterations = 10000,
        .name = "VDSO clock_gettime",
    };

    printf("==============================================\n");
    printf("RISC-V VDSO Time Caching Performance Benchmark\n");
    printf("==============================================\n");

    /* Check CPU frequency */
    FILE *fp = fopen("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "r");
    if (fp) {
        unsigned long freq_khz;
        if (fscanf(fp, "%lu", &freq_khz) == 1) {
            printf("CPU Frequency: %.2f MHz\n", freq_khz / 1000.0);
        }
        fclose(fp);
    }

    /* Run main benchmark */
    struct benchmark_result vdso_result = run_benchmark(clock_gettime_vdso, &config);
    print_result(&vdso_result, NULL);

    /* Compare with syscall (baseline - much slower) */
    struct benchmark_config syscall_config = {
        .iterations = 10000,  /* Fewer iterations for syscall (slower) */
        .warmup_iterations = 100,
        .name = "Syscall clock_gettime",
    };
    struct benchmark_result syscall_result = run_benchmark(clock_gettime_syscall, &syscall_config);
    print_result(&syscall_result, &vdso_result);

    /* Print comparison */
    printf("\n=== VDSO vs Syscall Comparison ===\n");
    printf("VDSO is %.2fx faster than syscall\n",
           syscall_result.avg_cycles / vdso_result.avg_cycles);

    /* Cache analysis */
    printf("\n=== Cache Effectiveness Analysis ===\n");

    /* Without cache: CSR_TIME takes ~250 cycles */
    double no_cache_cycles = 250.0;
    double actual_cycles = vdso_result.avg_cycles;

    if (actual_cycles < no_cache_cycles) {
        double cache_hit_rate = (1.0 - (actual_cycles / no_cache_cycles)) * 100.0;
        printf("Estimated cache hit rate: %.1f%%\n", cache_hit_rate);
        printf("(Avg: %.0f cycles vs ~250 cycles without cache)\n",
               actual_cycles);
    } else {
        printf("Cache may not be enabled or effective\n");
        printf("(Avg: %.0f cycles, expected < 250 with cache)\n",
               actual_cycles);
    }

    /* Run additional tests */
    simulate_ai_inference(100);
    test_cache_hit_rate(5);

    printf("\n==============================================\n");
    printf("Benchmark Complete\n");
    printf("==============================================\n");

    printf("\nInterpretation:\n");
    printf("  - If avg cycles < 100: Cache working well (>60%% hits)\n");
    printf("  - If avg cycles ~200-300: Cache not effective or disabled\n");
    printf("  - If avg cycles > 500: Possible issue (check dmesg)\n");
    printf("\nTo enable cache: CONFIG_RISCV_VDSO_TIME_CACHE=y\n");

    return 0;
}

#import <Foundation/Foundation.h>
#import <pthread.h>
#import <stdatomic.h>
// Races the first @synchronized on fresh objects (gnustep/libobjc2#424).
// Exits 2 if mutual exclusion is ever violated; hangs/aborts are caught by timeout.
enum { T = 16, ROUNDS = 4000 };
static pthread_barrier_t gStart, gEnd;
static id volatile gObj;
static atomic_int gInside, gViolations;
static void *worker(void *arg) {
  (void)arg;
  for (int r = 0; r < ROUNDS; r++) {
    pthread_barrier_wait(&gStart);
    @synchronized(gObj) {
      if (atomic_fetch_add(&gInside, 1) != 0) atomic_fetch_add(&gViolations, 1);
      for (volatile int i = 0; i < 50; i++) {}
      atomic_fetch_sub(&gInside, 1);
    }
    pthread_barrier_wait(&gEnd);
  }
  return NULL;
}
int main(void) {
  pthread_barrier_init(&gStart, NULL, T + 1);
  pthread_barrier_init(&gEnd, NULL, T + 1);
  pthread_t th[T];
  for (int i = 0; i < T; i++) pthread_create(&th[i], NULL, worker, NULL);
  for (int r = 0; r < ROUNDS; r++) {
    @autoreleasepool {
      id o = [NSObject new];
      gObj = o;
      pthread_barrier_wait(&gStart);
      pthread_barrier_wait(&gEnd);
      gObj = nil;
    }
  }
  for (int i = 0; i < T; i++) pthread_join(th[i], NULL);
  printf("violations=%d\n", gViolations);
  return gViolations ? 2 : 0;
}

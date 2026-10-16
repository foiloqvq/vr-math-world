#include <cstdio>
#include <numeric>
#include <vector>
int main() {
    std::vector<int> v(10);
    std::iota(v.begin(), v.end(), 1);
    int s = 0; for (int x : v) s += x;
    std::printf("hello-cpp OK  sum(1..10)=%d  __cplusplus=%ld\n", s, (long)__cplusplus);
    return s == 55 ? 0 : 1;
}
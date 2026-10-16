using System;
using System.Linq;
class Program {
    static int Main() {
        var sum = Enumerable.Range(1, 10).Sum();
        Console.WriteLine($"hello-cs OK  sum(1..10)={sum}  .NET {Environment.Version}");
        return sum == 55 ? 0 : 1;
    }
}
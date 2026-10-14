// RUN: %driver %s > %t.stdout 2> %t.stderr
// RUN: diff %t.stdout %s.stdout
int y = 7 + 100 * x;

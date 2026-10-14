// RUN: %driver %s > %t.stdout 2> %t.stderr
// RUN: diff %t.stdout %s.stdout
int n = 0x1F + 10;

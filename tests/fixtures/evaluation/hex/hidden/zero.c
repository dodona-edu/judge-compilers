// RUN: %driver %s > %t.stdout 2> %t.stderr
// RUN: diff %t.stdout %s.stdout
int z = 0 + 0x0;

#include <sstream>
#include <string>
#include <vector>

#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/raw_ostream.h"

// Implemented by the submission.
std::vector<std::string> integerLiterals(const std::string &source);

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  auto buffer = llvm::MemoryBuffer::getFile(argv[1]);
  if (!buffer)
    return 1;

  // The RUN lines contain digits that are not part of the program under test.
  std::istringstream lines((*buffer)->getBuffer().str());
  std::string line, source;
  while (std::getline(lines, line))
    if (line.rfind("// RUN:", 0) != 0)
      source += line + "\n";

  for (const std::string &literal : integerLiterals(source))
    llvm::outs() << literal << "\n";
  return 0;
}

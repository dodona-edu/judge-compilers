#include <cctype>
#include <string>
#include <vector>

std::vector<std::string> integerLiterals(const std::string &source) {
  std::vector<std::string> literals;
  size_t i = 0;
  while (i < source.size()) {
    if (std::isalpha(static_cast<unsigned char>(source[i])) || source[i] == '_') {
      while (i < source.size() && (std::isalnum(static_cast<unsigned char>(source[i])) || source[i] == '_'))
        i++;
    } else if (std::isdigit(static_cast<unsigned char>(source[i]))) {
      size_t start = i;
      while (i < source.size() && std::isalnum(static_cast<unsigned char>(source[i])))
        i++;
      std::string literal = source.substr(start, i - start);
      if (literal.rfind("0x", 0) != 0)
        literals.push_back(literal);
    } else {
      i++;
    }
  }
  return literals;
}

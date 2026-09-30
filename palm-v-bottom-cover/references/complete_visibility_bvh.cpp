// Exact triangle-ray visibility for the finite exterior comparison sample.
// Input mesh and query files contain a native uint64 count followed by doubles.
// Output byte 0 means all 26 directions were blocked; other values identify the
// first unblocked direction. A 0.00002 mm offset rejects self-intersections.
// The Python caller builds this helper in the system temporary directory.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <vector>
struct V {
  double v[3];
  double &operator[](int i) { return v[i]; }
  double operator[](int i) const { return v[i]; }
};
V operator-(V a, V b) { return {{a[0] - b[0], a[1] - b[1], a[2] - b[2]}}; }
V cross(V a, V b) {
  return {{a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
           a[0] * b[1] - a[1] * b[0]}};
}
double dot(V a, V b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
struct Tri {
  V a, b, c;
};
struct Node {
  V lo, hi;
  int l = -1, r = -1, start = 0, end = 0;
};
std::vector<Tri> tris;
std::vector<int> ids;
std::vector<Node> nodes;
int build(int a, int b) {
  Node n;
  n.lo = {{1e100, 1e100, 1e100}};
  n.hi = {{-1e100, -1e100, -1e100}};
  for (int k = a; k < b; ++k) {
    auto &t = tris[ids[k]];
    for (V p : {t.a, t.b, t.c})
      for (int j = 0; j < 3; ++j) {
        n.lo[j] = std::min(n.lo[j], p[j]);
        n.hi[j] = std::max(n.hi[j], p[j]);
      }
  }
  int idx = nodes.size();
  nodes.push_back(n);
  if (b - a <= 8) {
    nodes[idx].start = a;
    nodes[idx].end = b;
    return idx;
  }
  int axis = 0;
  for (int j = 1; j < 3; ++j)
    if (n.hi[j] - n.lo[j] > n.hi[axis] - n.lo[axis])
      axis = j;
  int mid = (a + b) / 2;
  std::nth_element(ids.begin() + a, ids.begin() + mid, ids.begin() + b,
                   [axis](int i, int j) {
                     auto &a = tris[i];
                     auto &b = tris[j];
                     return a.a[axis] + a.b[axis] + a.c[axis] <
                            b.a[axis] + b.b[axis] + b.c[axis];
                   });
  int l = build(a, mid), r = build(mid, b);
  nodes[idx].l = l;
  nodes[idx].r = r;
  return idx;
}
bool boxhit(Node &n, V o, V d) {
  double lo = 2e-5, hi = 1e100;
  for (int j = 0; j < 3; ++j) {
    if (std::abs(d[j]) < 1e-15) {
      if (o[j] < n.lo[j] - 1e-9 || o[j] > n.hi[j] + 1e-9)
        return false;
    } else {
      double a = (n.lo[j] - o[j]) / d[j], b = (n.hi[j] - o[j]) / d[j];
      if (a > b)
        std::swap(a, b);
      lo = std::max(lo, a);
      hi = std::min(hi, b);
      if (hi < lo)
        return false;
    }
  }
  return true;
}
bool trihit(Tri &t, V o, V d) {
  V e1 = t.b - t.a, e2 = t.c - t.a, h = cross(d, e2);
  double det = dot(e1, h);
  if (std::abs(det) < 1e-12)
    return false;
  V q = o - t.a;
  double a = dot(q, h) / det;
  if (a < -1e-9 || a > 1 + 1e-9)
    return false;
  V c = cross(q, e1);
  double b = dot(d, c) / det;
  if (b < -1e-9 || a + b > 1 + 1e-9)
    return false;
  return dot(e2, c) / det > 2e-5;
}
bool hit(V p, V d) {
  int stack[128], top = 0;
  stack[top++] = 0;
  while (top) {
    int k = stack[--top];
    auto &n = nodes[k];
    if (!boxhit(n, p, d))
      continue;
    if (n.l < 0) {
      for (int i = n.start; i < n.end; ++i)
        if (trihit(tris[ids[i]], p, d))
          return true;
    } else {
      stack[top++] = n.l;
      stack[top++] = n.r;
    }
  }
  return false;
}
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  std::ifstream in(argv[1], std::ios::binary), qp(argv[2], std::ios::binary);
  uint64_t n = 0, np = 0;
  in.read((char *)&n, 8);
  tris.resize(n);
  in.read((char *)tris.data(), n * sizeof(Tri));
  qp.read((char *)&np, 8);
  std::vector<V> p(np);
  qp.read((char *)p.data(), np * sizeof(V));
  if (!in || !qp)
    return 3;
  ids.resize(n);
  for (int i = 0; i < n; ++i)
    ids[i] = i;
  nodes.reserve(n / 4);
  build(0, n);
  std::vector<V> dirs = {{{0, 0, 1}},  {{0, 0, -1}}, {{1, 0, 0}},
                         {{-1, 0, 0}}, {{0, 1, 0}},  {{0, -1, 0}}};
  for (int x = -1; x <= 1; ++x)
    for (int y = -1; y <= 1; ++y)
      for (int z = -1; z <= 1; ++z)
        if ((x != 0) + (y != 0) + (z != 0) > 1) {
          double s = std::sqrt(x * x + y * y + z * z);
          dirs.push_back({{x / s, y / s, z / s}});
        }
  std::vector<uint8_t> out(np);
  int seen = 0;
  for (int i = 0; i < np; ++i) {
    for (int j = 0; j < dirs.size(); ++j)
      if (!hit(p[i], dirs[j])) {
        out[i] = j + 1;
        ++seen;
        break;
      }
  }
  std::ofstream f(argv[3], std::ios::binary);
  f.write((char *)out.data(), out.size());
  std::cout << seen << "/" << np << " exposed samples\n";
}

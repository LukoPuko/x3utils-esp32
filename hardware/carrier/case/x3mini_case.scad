// X3-Tuner Mini case (carrier board + plugged-in ESP32-C3 SuperMini + LiPo):
// the shared case model (../../case/case_core.scad) with this board's
// positions (board_data.scad, written by hardware/gen/make_case_data.py).
//
//   part = "bottom" | "lid"     single parts (STL)
//   part = "print"              both parts laid out for printing (lid upside down)
//   part = "assembly"           closed device (opaque, internals visible through the openings)
//   part = "xray"               see-through shell showing PCB, SuperMini and battery
//   part = "exploded"           exploded view
//   part = "section"            cutaway along the length (layer stack)

part = "assembly";
STL_PREFIX = "stl/x3mini-case-";   // USE_STL previews (relative to this file)

include <board_data.scad>
include <../../case/case_core.scad>

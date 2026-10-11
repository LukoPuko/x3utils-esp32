// X3-Tuner case: the shared case model (case_core.scad) with the X3-Tuner
// board positions (board_data.scad, written by hardware/gen/make_case_data.py).
//
//   part = "bottom" | "lid"     single parts (STL)
//   part = "print"              both parts laid out for printing (lid upside down)
//   part = "assembly"           closed device (opaque, internals visible through the openings)
//   part = "xray"               see-through shell showing PCB and battery
//   part = "exploded"           exploded view
//   part = "section"            cutaway along the length (layer stack)

part = "assembly";

include <board_data.scad>
include <case_core.scad>

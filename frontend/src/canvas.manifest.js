export const manifest = {
  screens: {
    scr_nx60x7: { name: "Home", route: "/", state: { "activeView": "home" }, position: { "x": 160, "y": 220 } },
    scr_1d4yig: { name: "Search", route: "/", state: { "activeView": "search" }, position: { "x": 1560, "y": 220 } },
    scr_dzx3xw: { name: "Library", route: "/", state: { "activeView": "library" }, position: { "x": 2960, "y": 220 } },
    scr_74baa7: { name: "Artist", route: "/", state: { "activeView": "artist", "selectedArtist": "a1" }, position: { "x": 0, "y": 0 }, isDefaultRow: true }
  },
  sections: {
    sec_s7m5ij: { name: "Main Navigation", x: 0, y: 0, width: 4320, height: 1180 }
  },
  layers: [
  { kind: "section", id: "sec_s7m5ij", children: [
    { kind: "screen", id: "scr_nx60x7" },
    { kind: "screen", id: "scr_1d4yig" },
    { kind: "screen", id: "scr_dzx3xw" }]
  },
  { kind: "screen", id: "scr_74baa7" }]

};
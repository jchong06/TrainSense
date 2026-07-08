// mapbox-gl ships no bundled types and @types/mapbox-gl isn't installed.
// The web map screen only needs it as an untyped module.
declare module "mapbox-gl";
declare module "mapbox-gl/dist/mapbox-gl.css";

import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Margin",
    short_name: "Margin",
    description: "Citation-backed analysis of government solicitations.",
    start_url: "/app",
    display: "standalone",
    background_color: "#F6F2E9",
    theme_color: "#F6F2E9",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
      { src: "/apple-icon.svg", sizes: "180x180", type: "image/svg+xml" },
    ],
  };
}

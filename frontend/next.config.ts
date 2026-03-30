import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Serveur autonome (node server.js) pour l'image Docker de déploiement
  output: "standalone",
};

export default nextConfig;

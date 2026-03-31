import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Serveur autonome (node server.js) pour l'image Docker de déploiement
  output: "standalone",
  // Pas de badge « N » du mode développement sur les pages (captures d'écran propres)
  devIndicators: false,
};

export default nextConfig;

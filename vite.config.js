import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // LOAD .env FILES BASED ON MODE (e.g., development, production)
  const env = loadEnv(mode, process.cwd());

  return {
    plugins: [react()],
    define: {
      "import.meta.env.VITE_OPENAI_API_KEY": JSON.stringify(
        env.VITE_OPENAI_API_KEY
      ),
    },
  };
});

# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

## Future Refinement: Takeaway Truncation

Current extraction quality is strongest when publishers provide clean `og:title` and `og:description` metadata. If future fallback extraction paths use longer raw page text, character-limit trimming should stay lightweight and deterministic.

When trimming takeaways, prefer the nearest complete sentence that fits the limit. Avoid mid-sentence cuts, trailing conjunctions or prepositions, and hard `...` fragments when a cleaner ending is available.

Avoid:

- `Currently, we have it set that it cuts the...`
- `The report explains how the city plans to...`

Prefer:

- `The report explains how the city plans to reduce emissions.`

If no complete sentence fits, fall back to the cleanest clause boundary. Hard truncation should remain the final fallback only. Do not add broad NLP summarization for this behavior.

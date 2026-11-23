// Conventional Commits (https://www.conventionalcommits.org), as @commitlint/config-conventional,
// except body and footer lines may be long: the history's bodies are written as paragraphs.
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'body-max-line-length': [0],
    'footer-max-line-length': [0],
  },
};

export default {
  resolve: {
    // Bypass fs.realpathSync.native EPERM on Windows while resolving node_modules packages in Vitest.
    preserveSymlinks: true,
  },
};


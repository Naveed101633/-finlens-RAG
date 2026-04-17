{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.python312Packages.venv
  ];
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.libffi
      pkgs.openssl
    ];
    LANG = "en_US.UTF-8";
    LOCALE_ARCHIVE = "${pkgs.glibcLocales}/lib/locale/locale-archive";
  };
}

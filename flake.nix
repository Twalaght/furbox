{
  description = "furbox, packaged using uv2nix";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs = {
        pyproject-nix.follows = "pyproject-nix";
        uv2nix.follows = "uv2nix";
        nixpkgs.follows = "nixpkgs";
      };
    };
  };

  outputs = {
    nixpkgs,
    pyproject-nix,
    uv2nix,
    pyproject-build-systems,
    ...
  }: let
    packageName = "furbox";
    pythonVersion = "python314";
    sourcePreference = "wheel";
    src = ./.;

    inherit (nixpkgs) lib;
    forAllSystems = lib.genAttrs lib.systems.flakeExposed;

    # Set up the workspace using the UV lockfile.
    workspace = uv2nix.lib.workspace.loadWorkspace {workspaceRoot = src;};
    overlay = workspace.mkPyprojectOverlay {inherit sourcePreference;};

    pythonSets = forAllSystems (
      system: let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.${pythonVersion};
      in
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope
        (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.${sourcePreference}
            overlay
          ]
        )
    );
  in {
    packages = forAllSystems (
      system: let
        pythonSet = pythonSets.${system};
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (pkgs.callPackages pyproject-nix.build.util {}) mkApplication;
      in {
        # Create a derivation that wraps the env but that only links package content
        # present in pythonSet.${packageName}, excluding additional components
        # of the virtual environment like the python interpreter and scripts.
        default = mkApplication {
          venv = pythonSet.mkVirtualEnv "${packageName}-env" workspace.deps.default;
          package = pythonSet.${packageName};
        };
      }
    );
  };
}

import os
import re
import subprocess
from typing import Literal, cast, get_args
from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext
from setuptools.command.sdist import sdist
try:
    from setuptools.command.bdist_wheel import bdist_wheel
except ImportError:
    from wheel.bdist_wheel import bdist_wheel  # type: ignore

System = Literal["Windows", "Linux", "Darwin"]
Arch = Literal["x64", "x86", "arm", "arm64", "x86_64"]

# FIX: Use __file__ instead of 'file' variable which was undefined in original snippet
INSTALL_DIR = os.path.dirname(os.path.realpath(__file__)) 

# FIX: Changed directory name to match your new folder structure
ARISUFXPYBOOST_DIR = os.path.join(INSTALL_DIR, "ArisuFxPyBoost")

class BuildExt(build_ext):
    def build_extensions(self):
        cpp_version_flag: str
        compiler = self.compiler
        
        # msvc - only ever used c++20, never c++2a
        if compiler.compiler_type == "msvc":
            cpp_version_flag = "/std:c++20"
        # gnu & clang
        elif compiler.compiler_type == "unix":
            res = subprocess.run(
                [compiler.compiler[0], "-v"],
                capture_output=True,
            )
            # for some reason g++ and clang++ return this as error
            text = (res.stdout or res.stderr).decode("utf-8")
            version = re.search(r"version\s+(\d+)\.", text)
            if version is None:
                raise Exception("Failed to determine compiler version")
            version = int(version.group(1))
            cpp_version_flag = "-std=c++2a" if version < 10 else "-std=c++20"
        else:
            cpp_version_flag = "-std=c++20"

        for ext in self.extensions:
            ext.extra_compile_args = [cpp_version_flag]
        build_ext.build_extensions(self)

class SDist(sdist):
    def make_distribution(self) -> None:
        # add all fmod libraries to the distribution
        # FIX: Updated path to ArisuFxPy/lib/FMOD
        for root, _dirs, files in os.walk("ArisuFxPy/lib/FMOD"):
            for file in files:
                fp = f"{root}/{file}"
                if fp not in self.filelist.files:
                    self.filelist.files.append(fp)
        return super().make_distribution()

BDIST_TAG_FMOD_MAP = {
    # Windows
    "win32": "x86",
    "win_amd64": "x64",
    "win_arm64": "arm",
    # Linux and Mac endings
    "arm64": "arm64",  # Mac
    "x86_64": "x64",
    "aarch64": "arm64",  # Linux
    "i686": "x86",
    "armv7l": "arm",  # armhf
}

def get_fmod_path(system: System, arch: Arch) -> str:
    if system == "Darwin":
        # universal dylib
        return "lib/FMOD/Darwin/libfmod.dylib"
    if system == "Windows":
        return f"lib/FMOD/Windows/{arch}/fmod.dll"
    if system == "Linux":
        if arch == "x64":
            arch = "x86_64"
        return f"lib/FMOD/Linux/{arch}/libfmod.so"
    raise NotImplementedError(f"Unsupported system: {system}")

class BDistWheel(bdist_wheel):  # type: ignore
    def run(self):
        platform_tag = self.get_tag()[2]
        if platform_tag.startswith("win"):
            system = "Windows"
            arch = BDIST_TAG_FMOD_MAP[platform_tag]
        else:
            arch = next(
                (v for k, v in BDIST_TAG_FMOD_MAP.items() if platform_tag.endswith(k)),
                None,
            )
            system = "Darwin" if platform_tag.startswith("macosx") else "Linux"

        if arch and arch in get_args(Arch):
            # FIX: Updated package data key to ArisuFxPy
            self.distribution.package_data["ArisuFxPy"].append(get_fmod_path(system, cast(Arch, arch)))
        super().run()

setup(
    # FIX: Package Name changed to ArisuFxPy
    name="ArisuFxPy",
    packages=find_packages(),
    # FIX: Resources path updated inside ArisuFxPy folder
    package_data={"ArisuFxPy": ["resources/lzma.tpk"]},
    ext_modules=[
        Extension(
            # FIX: Module name updated to match folder structure
            "ArisuFxPy.ArisuFxPyBoost",
            # FIX: Source files now come from ArisuFxPyBoost folder
            [f"ArisuFxPyBoost/{f}" for f in os.listdir(ARISUFXPYBOOST_DIR) if f.endswith(".cpp")],
            depends=[f"ArisuFxPyBoost/{f}" for f in os.listdir(ARISUFXPYBOOST_DIR) if f.endswith(".hpp")],
            language="c++",
            include_dirs=[ARISUFXPYBOOST_DIR],
        )
    ],
    cmdclass={"build_ext": BuildExt, "sdist": SDist, "bdist_wheel": BDistWheel},
)
from scripts.xilinx_tools import find_mingw_runtime_bin


def test_installed_mingw_runtime_has_cosim_dlls_when_present() -> None:
    runtime = find_mingw_runtime_bin()
    if runtime is None:
        return
    assert (runtime / "libstdc++-6.dll").is_file()
    assert (runtime / "libgcc_s_seh-1.dll").is_file()

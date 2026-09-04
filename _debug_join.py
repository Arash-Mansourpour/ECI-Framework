"""Debug the ECIFramework network path."""
import sys, asyncio

sys.path.insert(0, "src")
from eci.framework import ECIFramework


async def main():
    fw = ECIFramework()
    init = await fw.initialize_network()
    print("init:", init["status"], init["seed_node"][:16])
    for i in range(3):
        r = await fw.network_manager.join_network(
            {"tflops": 2.0 + i, "memory_gb": 16.0, "bandwidth_mbps": 200.0}
        )
        print(f"join {i}:", r)
    mgr = fw.network_manager
    prof = await mgr._measure_consciousness(seed=2)
    print("direct measure seed=2(+42):", prof.phi_value)


asyncio.run(main())

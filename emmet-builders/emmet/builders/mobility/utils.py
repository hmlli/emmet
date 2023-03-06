from pymatgen.entries.computed_entries import ComputedStructureEntry

def get_base_cse_from_non_base(host, ie):
    chg_entry = ie.fully_charged_entry
    num_wi = ie.fully_charged_entry.structure.composition[ie.working_ion]
    wi_energy = ie.working_ion_entry.energy

    estimate_energy = chg_entry.energy - num_wi * wi_energy
    empty_host_cse = ComputedStructureEntry(structure=host, energy=estimate_energy)

    return empty_host_cse
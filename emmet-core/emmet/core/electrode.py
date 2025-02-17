import re
from datetime import datetime
from typing import List, Union, Dict
from collections import defaultdict

from monty.json import MontyDecoder
from pydantic import BaseModel, Field, validator
from pymatgen.apps.battery.battery_abc import AbstractElectrode
from pymatgen.apps.battery.conversion_battery import ConversionElectrode
from pymatgen.apps.battery.insertion_battery import InsertionElectrode
from pymatgen.core import Composition, Structure
from pymatgen.core.periodic_table import Element
from pymatgen.entries.computed_entries import ComputedEntry, ComputedStructureEntry

from emmet.core.mpid import MPID


class VoltagePairDoc(BaseModel):
    """
    Data for individual voltage steps.
    Note: Each voltage step is represented as a sub_electrode (ConversionElectrode/InsertionElectrode)
        object to gain access to some basic statistics about the voltage step
    """

    max_delta_volume: float = Field(
        None,
        description="Volume changes in % for a particular voltage step using: "
        "max(charge, discharge) / min(charge, discharge) - 1.",
    )

    average_voltage: float = Field(
        None, description="The average voltage in V for a particular voltage step."
    )

    capacity_grav: float = Field(None, description="Gravimetric capacity in mAh/g.")

    capacity_vol: float = Field(None, description="Volumetric capacity in mAh/cc.")

    energy_grav: float = Field(
        None, description="Gravimetric energy (Specific energy) in Wh/kg."
    )

    energy_vol: float = Field(
        None, description="Volumetric energy (Energy Density) in Wh/l."
    )

    fracA_charge: float = Field(
        None, description="Atomic fraction of the working ion in the charged state."
    )

    fracA_discharge: float = Field(
        None, description="Atomic fraction of the working ion in the discharged state."
    )

    @classmethod
    def from_sub_electrode(cls, sub_electrode: AbstractElectrode, **kwargs):
        """
        Convert A pymatgen electrode object to a document
        """
        return cls(**sub_electrode.get_summary_dict(), **kwargs)


class InsertionVoltagePairDoc(VoltagePairDoc):
    """
    Features specific to insertion electrode
    """

    formula_charge: str = Field(
        None, description="The chemical formula of the charged material."
    )

    formula_discharge: str = Field(
        None, description="The chemical formula of the discharged material."
    )

    stability_charge: float = Field(
        None, description="The energy above hull of the charged material in eV/atom."
    )

    stability_discharge: float = Field(
        None, description="The energy above hull of the discharged material in eV/atom."
    )

    id_charge: Union[MPID, int, None] = Field(
        None, description="The Materials Project ID of the charged structure."
    )

    id_discharge: Union[MPID, int, None] = Field(
        None, description="The Materials Project ID of the discharged structure."
    )


class EntriesCompositionSummary(BaseModel):
    """
    Composition summary data for all material entries associated with this electrode.
    Included to enable better searching via the API.
    """

    all_formulas: List[str] = Field(
        None,
        description="Reduced formulas for material entries across all voltage pairs.",
    )

    all_chemsys: List[str] = Field(
        None,
        description="Chemical systems for material entries across all voltage pairs.",
    )

    all_formula_anonymous: List[str] = Field(
        None,
        description="Anonymous formulas for material entries across all voltage pairs.",
    )

    all_elements: List[Element] = Field(
        None,
        description="Elements in material entries across all voltage pairs.",
    )

    all_composition_reduced: Dict = Field(
        None,
        description="Composition reduced data for entries across all voltage pairs.",
    )

    @classmethod
    def from_compositions(cls, compositions: List[Composition]):

        all_formulas = list({comp.reduced_formula for comp in compositions})
        all_chemsys = list({comp.chemical_system for comp in compositions})
        all_formula_anonymous = list({comp.anonymized_formula for comp in compositions})
        all_elements = sorted(compositions)[-1].elements

        all_composition_reduced = defaultdict(set)

        for comp in compositions:
            comp_red = comp.get_reduced_composition_and_factor()[0].as_dict()

            for ele, num in comp_red.items():
                all_composition_reduced[ele].add(num)

        return cls(
            all_formulas=all_formulas,
            all_chemsys=all_chemsys,
            all_formula_anonymous=all_formula_anonymous,
            all_elements=all_elements,
            all_composition_reduced=all_composition_reduced,
        )


class InsertionElectrodeDoc(InsertionVoltagePairDoc):
    """
    Insertion electrode
    """

    battery_id: str = Field(None, description="The id for this battery document.")

    battery_formula: str = Field(
        None,
        description="Reduced formula with working ion range produced by combining the charge and discharge formulas.",
    )

    framework_formula: str = Field(
        None, description="The id for this battery document."
    )

    host_structure: Structure = Field(
        None, description="Host structure (structure without the working ion)."
    )

    adj_pairs: List[InsertionVoltagePairDoc] = Field(
        None, description="Returns all of the voltage steps material pairs."
    )

    working_ion: Element = Field(
        None, description="The working ion as an Element object."
    )

    num_steps: int = Field(
        None,
        description="The number of distinct voltage steps in from fully charge to "
        "discharge based on the stable intermediate states.",
    )

    max_voltage_step: float = Field(
        None, description="Maximum absolute difference in adjacent voltage steps."
    )

    last_updated: datetime = Field(
        None,
        description="Timestamp for the most recent calculation for this Material document.",
    )

    framework: Composition = Field(
        None, description="The chemical compositions of the host framework."
    )

    elements: List[Element] = Field(
        None,
        description="The atomic species contained in this electrode (not including the working ion).",
    )

    nelements: int = Field(
        None,
        description="The number of elements in the material (not including the working ion).",
    )

    chemsys: str = Field(
        None,
        description="The chemical system this electrode belongs to (not including the working ion).",
    )

    material_ids: List[MPID] = Field(
        None,
        description="The ids of all structures that matched to the present host lattice, regardless of stability. "
        "The stable entries can be found in the adjacent pairs.",
    )

    formula_anonymous: str = Field(
        None,
        title="Anonymous Formula",
        description="Anonymized representation of the formula (not including the working ion).",
    )

    entries_composition_summary: EntriesCompositionSummary = Field(
        None,
        description="Composition summary data for all material in entries across all voltage pairs.",
    )

    electrode_object: InsertionElectrode = Field(
        None, description="The Pymatgen electrode object."
    )

    warnings: List[str] = Field(
        [], description="Any warnings related to this electrode data."
    )

    # Make sure that the datetime field is properly formatted
    @validator("last_updated", pre=True)
    def last_updated_dict_ok(cls, v):
        return MontyDecoder().process_decoded(v)

    @classmethod
    def from_entries(
        cls,
        grouped_entries: List[ComputedStructureEntry],
        working_ion_entry: ComputedEntry,
        battery_id: str,
        strip_structures: bool = False,
    ) -> Union["InsertionElectrodeDoc", None]:
        try:
            ie = InsertionElectrode.from_entries(
                entries=grouped_entries,
                working_ion_entry=working_ion_entry,
                strip_structures=strip_structures,
            )
        except IndexError:
            return None
        # First get host structure

        d = ie.get_summary_dict()

        least_wion_ent = next(
            item for item in grouped_entries if item.entry_id == d["id_charge"]
        )
        host_structure = least_wion_ent.structure.copy()
        host_structure.remove_species([d["working_ion"]])

        d["material_ids"] = d["stable_material_ids"] + d["unstable_material_ids"]
        d["num_steps"] = d.pop("nsteps", None)
        d["last_updated"] = datetime.utcnow()
        elements = sorted(host_structure.composition.elements)
        chemsys = "-".join(sorted(map(str, elements)))
        framework = Composition(d["framework_formula"])
        discharge_comp = Composition(d["formula_discharge"])
        working_ion_ele = Element(d["working_ion"])
        battery_formula = cls.get_battery_formula(
            Composition(d["formula_charge"]),
            discharge_comp,
            working_ion_ele,
        )

        compositions = []
        for doc in d["adj_pairs"]:
            compositions.append(Composition(doc["formula_charge"]))
            compositions.append(Composition(doc["formula_discharge"]))

        entries_composition_summary = EntriesCompositionSummary.from_compositions(
            compositions
        )

        # Check if more than one working ion per transition metal and warn
        warnings = []
        transition_metal_fraction = sum(
            [
                discharge_comp.get_atomic_fraction(element)
                for element in discharge_comp
                if element.is_transition_metal
            ]
        )
        if (
            discharge_comp.get_atomic_fraction(working_ion_ele)
            / transition_metal_fraction
            > 1.0
        ):
            warnings.append("More than one working ion per transition metal")

        return cls(
            battery_id=battery_id,
            host_structure=host_structure.as_dict(),
            framework=framework,
            battery_formula=battery_formula,
            electrode_object=ie.as_dict(),
            elements=elements,
            nelements=len(elements),
            chemsys=chemsys,
            formula_anonymous=framework.anonymized_formula,
            entries_composition_summary=entries_composition_summary,
            warnings=warnings,
            **d,
        )

    @staticmethod
    def get_battery_formula(
        charge_comp: Composition, discharge_comp: Composition, working_ion: Element
    ):

        working_ion_subscripts = []

        for comp in [charge_comp, discharge_comp]:

            comp_dict = comp.get_el_amt_dict()

            working_ion_num = (
                comp_dict.pop(working_ion.value)
                if working_ion.value in comp_dict
                else 0
            )
            temp_comp = Composition.from_dict(comp_dict)

            (temp_reduced, n) = temp_comp.get_reduced_composition_and_factor()

            new_subscript = re.sub(".00$", "", "{:.2f}".format(working_ion_num / n))
            if new_subscript != "0":
                new_subscript = new_subscript.rstrip("0")

            working_ion_subscripts.append(new_subscript)

        return (
            working_ion.value
            + "-".join(working_ion_subscripts)
            + temp_reduced.reduced_formula
        )


class ConversionVoltagePairDoc(VoltagePairDoc):
    """
    Features specific to conversion electrode
    """

    reactions: List[str] = Field(
        None,
        description="The reaction(s) the characterizes that particular voltage step.",
    )


class ConversionElectrodeDoc(ConversionVoltagePairDoc):
    battery_id: str = Field(None, description="The id for this battery document.")

    adj_pairs: List[ConversionVoltagePairDoc] = Field(
        None, description="Returns all the adjacent Voltage Steps"
    )

    working_ion: Element = Field(
        None, description="The working ion as an Element object"
    )

    num_steps: int = Field(
        None,
        description="The number of distinct voltage steps in from fully charge to "
        "discharge based on the stable intermediate states",
    )

    max_voltage_step: float = Field(
        None, description="Maximum absolute difference in adjacent voltage steps"
    )

    last_updated: datetime = Field(
        None,
        description="Timestamp for the most recent calculation for this Material document",
    )

    # Make sure that the datetime field is properly formatted
    @validator("last_updated", pre=True)
    def last_updated_dict_ok(cls, v):
        return MontyDecoder().process_decoded(v)

    @classmethod
    def from_composition_and_entries(
        cls,
        composition: Composition,
        entries: List[ComputedEntry],
        working_ion_symbol: str,
        task_id: MPID,
    ):
        ce = ConversionElectrode.from_composition_and_entries(
            comp=composition,
            entries_in_chemsys=entries,
            working_ion_symbol=working_ion_symbol,
        )
        d = ce.get_summary_dict()
        d["num_steps"] = d.pop("nsteps", None)
        d["last_updated"] = datetime.utcnow()
        return cls(task_id=task_id, framework=Composition(d["framework_formula"]), **d)

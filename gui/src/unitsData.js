/*
 * Copyright The NOMAD Authors.
 *
 * This file is part of NOMAD. See https://nomad-lab.eu for further info.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
// Generated by NOMAD CLI. Do not edit manually.
export const unitMap = {
  second: {
    dimension: 'time',
    label: 'Second',
    abbreviation: 's'
  },
  atomic_unit_of_time: {
    dimension: 'time',
    label: 'Atomic unit of time',
    abbreviation: 'a_u_time'
  },
  meter: {
    dimension: 'length',
    label: 'Meter',
    abbreviation: 'm'
  },
  bohr: {
    dimension: 'length',
    label: 'Bohr',
    abbreviation: 'bohr'
  },
  angstrom: {
    dimension: 'length',
    label: '\u00c5ngstrom',
    abbreviation: '\u00c5'
  },
  kilogram: {
    dimension: 'mass',
    label: 'Kilogram',
    abbreviation: 'kg'
  },
  electron_mass: {
    dimension: 'mass',
    label: 'Electron mass',
    abbreviation: 'm\u2091'
  },
  unified_atomic_mass_unit: {
    dimension: 'mass',
    label: 'Unified atomic mass unit',
    abbreviation: 'u'
  },
  ampere: {
    dimension: 'current',
    label: 'Ampere',
    abbreviation: 'A'
  },
  atomic_unit_of_current: {
    dimension: 'current',
    label: 'Atomic unit of current',
    abbreviation: 'a_u_current'
  },
  mole: {
    dimension: 'substance',
    label: 'Mole',
    abbreviation: 'mole'
  },
  candela: {
    dimension: 'luminosity',
    label: 'Candela',
    abbreviation: 'cd'
  },
  kelvin: {
    dimension: 'temperature',
    label: 'Kelvin',
    abbreviation: 'K'
  },
  celsius: {
    dimension: 'temperature',
    label: 'Celsius',
    abbreviation: '\u00b0C'
  },
  fahrenheit: {
    dimension: 'temperature',
    label: 'Fahrenheit',
    abbreviation: '\u00b0F'
  },
  atomic_unit_of_temperature: {
    dimension: 'temperature',
    label: 'Atomic unit of temperature',
    abbreviation: 'a_u_temperature'
  },
  newton: {
    dimension: 'force',
    label: 'Newton',
    abbreviation: 'N'
  },
  atomic_unit_of_force: {
    dimension: 'force',
    label: 'Atomic unit of force',
    abbreviation: 'a_u_force'
  },
  pascal: {
    dimension: 'pressure',
    label: 'Pascal',
    abbreviation: 'Pa'
  },
  gigapascal: {
    dimension: 'pressure',
    label: 'Gigapascal',
    abbreviation: 'GPa'
  },
  atomic_unit_of_pressure: {
    dimension: 'pressure',
    label: 'Atomic unit of pressure',
    abbreviation: 'a_u_pressure'
  },
  joule: {
    dimension: 'energy',
    label: 'Joule',
    abbreviation: 'J'
  },
  electron_volt: {
    dimension: 'energy',
    label: 'Electron volt',
    abbreviation: 'eV'
  },
  hartree: {
    dimension: 'energy',
    label: 'Hartree',
    abbreviation: 'Ha'
  },
  watt: {
    dimension: 'power',
    label: 'Watt',
    abbreviation: 'W'
  },
  hertz: {
    dimension: 'frequency',
    label: 'Hertz',
    abbreviation: 'Hz'
  },
  volt: {
    dimension: 'electric_potential',
    label: 'Volt',
    abbreviation: 'V'
  },
  farad: {
    dimension: 'capacitance',
    label: 'Farad',
    abbreviation: 'F'
  },
  coulomb: {
    dimension: 'charge',
    label: 'Coulomb',
    abbreviation: 'C'
  },
  elementary_charge: {
    dimension: 'charge',
    label: 'Elementary charge',
    abbreviation: 'e'
  },
  tesla: {
    dimension: 'magnetic_field',
    label: 'Tesla',
    abbreviation: 'T'
  },
  weber: {
    dimension: 'magnetic_flux',
    label: 'Weber',
    abbreviation: 'Wb'
  },
  bohr_magneton: {
    dimension: 'magnetic_dipole',
    label: 'Bohr magneton',
    abbreviation: 'Bm'
  },
  henry: {
    dimension: 'inductance',
    label: 'Henry',
    abbreviation: 'H'
  },
  radian: {
    dimension: 'angle',
    label: 'Radian',
    abbreviation: 'rad'
  },
  degree: {
    dimension: 'angle',
    label: 'Degree',
    abbreviation: '\u00b0'
  },
  dimensionless: {
    dimension: 'dimensionless',
    label: 'Dimensionless',
    abbreviation: ''
  }
}
export const conversionMap = {
  time: {
    units: [
      'second',
      'atomic_unit_of_time'
    ],
    multipliers: {
      second: {
        second: 1,
        atomic_unit_of_time: 4.134137333518244e+16
      },
      atomic_unit_of_time: {
        second: 2.4188843265856806e-17,
        atomic_unit_of_time: 1
      }
    }
  },
  length: {
    units: [
      'meter',
      'bohr',
      'angstrom'
    ],
    multipliers: {
      meter: {
        meter: 1,
        bohr: 18897261246.22279,
        angstrom: 10000000000.0
      },
      bohr: {
        meter: 5.2917721090397754e-11,
        bohr: 1,
        angstrom: 0.5291772109039775
      },
      angstrom: {
        meter: 1e-10,
        bohr: 1.8897261246222794,
        angstrom: 1
      }
    }
  },
  mass: {
    units: [
      'kilogram',
      'electron_mass',
      'unified_atomic_mass_unit'
    ],
    multipliers: {
      kilogram: {
        kilogram: 1,
        electron_mass: 1.0977691057577633e+30,
        unified_atomic_mass_unit: 6.022140762081123e+26
      },
      electron_mass: {
        kilogram: 9.1093837015e-31,
        electron_mass: 1,
        unified_atomic_mass_unit: 0.0005485799090624057
      },
      unified_atomic_mass_unit: {
        kilogram: 1.6605390666e-27,
        electron_mass: 1822.8884862173131,
        unified_atomic_mass_unit: 1
      }
    }
  },
  current: {
    units: [
      'ampere',
      'atomic_unit_of_current'
    ],
    multipliers: {
      ampere: {
        ampere: 1,
        atomic_unit_of_current: 150.97488474455437
      },
      atomic_unit_of_current: {
        ampere: 0.006623618237509995,
        atomic_unit_of_current: 1
      }
    }
  },
  substance: {
    units: [
      'mole'
    ],
    multipliers: {
      mole: {
        mole: 1
      }
    }
  },
  luminosity: {
    units: [
      'candela'
    ],
    multipliers: {
      candela: {
        candela: 1
      }
    }
  },
  temperature: {
    units: [
      'kelvin',
      'celsius',
      'fahrenheit',
      'atomic_unit_of_temperature'
    ],
    multipliers: {
      kelvin: {
        kelvin: 1,
        celsius: 1.0,
        fahrenheit: 1.7999999999999998,
        atomic_unit_of_temperature: 3.1668115634555572e-06
      },
      celsius: {
        kelvin: 1,
        celsius: 1,
        fahrenheit: 1.7999999999999998,
        atomic_unit_of_temperature: 3.1668115634555572e-06
      },
      fahrenheit: {
        kelvin: 0.5555555555555556,
        celsius: 0.5555555555555556,
        fahrenheit: 1,
        atomic_unit_of_temperature: 1.7593397574753097e-06
      },
      atomic_unit_of_temperature: {
        kelvin: 315775.0248040719,
        celsius: 315775.0248040719,
        fahrenheit: 568395.0446473294,
        atomic_unit_of_temperature: 1
      }
    },
    constants: {
      kelvin: {
        celsius: -273.15,
        fahrenheit: -459.67
      },
      celsius: {
        celsius: -273.15,
        fahrenheit: -459.67
      },
      fahrenheit: {
        celsius: -273.15,
        fahrenheit: -459.67
      },
      atomic_unit_of_temperature: {
        celsius: -273.15,
        fahrenheit: -459.67
      }
    }
  },
  force: {
    units: [
      'newton',
      'atomic_unit_of_force'
    ],
    multipliers: {
      newton: {
        newton: 1,
        atomic_unit_of_force: 12137802.66097955
      },
      atomic_unit_of_force: {
        newton: 8.238723498238991e-08,
        atomic_unit_of_force: 1
      }
    }
  },
  pressure: {
    units: [
      'pascal',
      'gigapascal',
      'atomic_unit_of_pressure'
    ],
    multipliers: {
      pascal: {
        pascal: 1,
        gigapascal: 1.0000000000000003e-09,
        atomic_unit_of_pressure: 3.3989309217619455e-14
      },
      gigapascal: {
        pascal: 1000000000.0,
        gigapascal: 1,
        atomic_unit_of_pressure: 3.398930921761947e-05
      },
      atomic_unit_of_pressure: {
        pascal: 29421015696359.54,
        gigapascal: 29421.015696359544,
        atomic_unit_of_pressure: 1
      }
    }
  },
  energy: {
    units: [
      'joule',
      'electron_volt',
      'hartree'
    ],
    multipliers: {
      joule: {
        joule: 1,
        electron_volt: 6.241509074460763e+18,
        hartree: 2.2937122783962883e+17
      },
      electron_volt: {
        joule: 1.602176634e-19,
        electron_volt: 1,
        hartree: 0.03674932217565436
      },
      hartree: {
        joule: 4.35974472220717e-18,
        electron_volt: 27.21138624598847,
        hartree: 1
      }
    }
  },
  power: {
    units: [
      'watt'
    ],
    multipliers: {
      watt: {
        watt: 1
      }
    }
  },
  frequency: {
    units: [
      'hertz'
    ],
    multipliers: {
      hertz: {
        hertz: 1
      }
    }
  },
  electric_potential: {
    units: [
      'volt'
    ],
    multipliers: {
      volt: {
        volt: 1
      }
    }
  },
  capacitance: {
    units: [
      'farad'
    ],
    multipliers: {
      farad: {
        farad: 1
      }
    }
  },
  charge: {
    units: [
      'coulomb',
      'elementary_charge'
    ],
    multipliers: {
      coulomb: {
        coulomb: 1,
        elementary_charge: 6.241509074460763e+18
      },
      elementary_charge: {
        coulomb: 1.602176634e-19,
        elementary_charge: 1
      }
    }
  },
  magnetic_field: {
    units: [
      'tesla'
    ],
    multipliers: {
      tesla: {
        tesla: 1
      }
    }
  },
  magnetic_flux: {
    units: [
      'weber'
    ],
    multipliers: {
      weber: {
        weber: 1
      }
    }
  },
  magnetic_dipole: {
    units: [
      'bohr_magneton'
    ],
    multipliers: {
      bohr_magneton: {
        bohr_magneton: 1
      }
    }
  },
  inductance: {
    dimension: 'inductance',
    units: [
      'henry'
    ],
    multipliers: {
      henry: {
        henry: 1
      }
    }
  },
  angle: {
    dimension: 'angle',
    units: [
      'radian',
      'degree'
    ],
    multipliers: {
      radian: {
        radian: 1,
        degree: 57.29577951308232
      },
      degree: {
        radian: 0.017453292519943295,
        degree: 1
      }
    }
  },
  dimensionless: {
    dimension: 'dimensionless',
    units: [
      'dimensionless'
    ],
    multipliers: {
      dimensionless: {
        dimensionless: 1
      }
    }
  }
}
export const unitSystems = {
  SI: {
    label: 'SI',
    description: 'International System of Units (SI)',
    units: {
      time: 'second',
      length: 'meter',
      mass: 'kilogram',
      current: 'ampere',
      substance: 'mole',
      luminosity: 'candela',
      temperature: 'kelvin',
      force: 'newton',
      pressure: 'pascal',
      energy: 'joule',
      power: 'watt',
      frequency: 'hertz',
      electric_potential: 'volt',
      charge: 'coulomb',
      angle: 'radian'
    }
  },
  AU: {
    label: 'Atomic units',
    description: 'Hartree atomic units',
    units: {
      time: 'atomic_unit_of_time',
      length: 'bohr',
      mass: 'electron_mass',
      current: 'atomic_unit_of_current',
      temperature: 'atomic_unit_of_temperature',
      force: 'atomic_unit_of_force',
      energy: 'hartree',
      pressure: 'atomic_unit_of_pressure',
      angle: 'radian'
    }
  }
}

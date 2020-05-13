from astropy.modeling import models, powerlaws
import astropy.units as u

def get_params(model_dict):
    return {x["name"]: u.Quantity(x["value"], x["unit"]) for x in model_dict["parameters"]}

def get_fixed(model_dict):
    return {x["name"]: x["fixed"] for x in model_dict["parameters"]}

def initialize_gaussian1d(params, fixed, name):
    return models.Gaussian1D(amplitude=params["amplitude"],
                             mean=params["mean"],
                             stddev=params["stddev"],
                             name=name,
                             fixed = fixed)

def initialize_const1d(params, fixed, name):
    return models.Const1D(amplitude=params["amplitude"],
                          name=name,
                          fixed = fixed)

def initialize_linear1d(params, fixed, name):
    return models.Linear1D(slope=params["slope"],
                           intercept=params["intercept"],
                           name=name,
                           fixed=fixed)

def initialize_powerlaw1d(params, fixed, name):
    return powerlaws.PowerLaw1D(amplitude=params["amplitude"],
                                x_0=params["x_0"],
                                alpha=params["alpha"],
                                name=name,
                                fixed=fixed)

def initialize_lorentz1d(params, fixed, name):
    return models.Lorentz1D(amplitude=params["amplitude"],
                            x_0=params["x_0"],
                            fwhm=params["fwhm"],
                            name=name,
                            fixed=fixed)

def initialize_voigt1d(params, fixed, name):
    return models.Voigt1D(x_0=params["x_0"],
                          amplitude_L=params["amplitude_L"],
                          fwhm_L=params["fwhm_L"],
                          fwhm_G=params["fwhm_G"],
                          name=name,
                          fixed=fixed)

model_initializers = {"Gaussian1D": initialize_gaussian1d,
                      "Const1D": initialize_const1d,
                      "Linear1D": initialize_linear1d,
                      "PowerLaw1D": initialize_powerlaw1d,
                      "Lorentz1D": initialize_lorentz1d,
                      "Voigt1D": initialize_voigt1d,
                      }

model_parameters = {"Gaussian1D": ["amplitude", "stddev", "mean"],
                    "Const1D": ["amplitude"],
                    "Linear1D": ["slope", "intercept"],
                    "PowerLaw1D": ["amplitude", "x_0", "alpha"],
                    "Lorentz1D": ["amplitude", "x_0", "fwhm"],
                    "Voigt1D": ["x_0", "amplitude_L", "fwhm_L", "fwhm_G"],
                    }

def initialize_model(model_dict):
    params = get_params(model_dict)
    fixed = get_fixed(model_dict)
    return model_initializers[model_dict["model_type"]](params, fixed, model_dict["id"])

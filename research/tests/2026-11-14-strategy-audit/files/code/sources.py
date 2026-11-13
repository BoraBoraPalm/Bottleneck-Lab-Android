"""Fixed source list of the strategy audit (declared before any data was seen)."""

FRENCH_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"

FRENCH_US = [
    "F-F_Research_Data_Factors", "F-F_Research_Data_Factors_daily",
    "F-F_Research_Data_5_Factors_2x3", "F-F_Momentum_Factor",
    "Portfolios_Formed_on_ME", "Portfolios_Formed_on_BE-ME", "Portfolios_Formed_on_OP",
    "Portfolios_Formed_on_INV", "Portfolios_Formed_on_E-P", "Portfolios_Formed_on_CF-P",
    "Portfolios_Formed_on_D-P", "Portfolios_Formed_on_AC", "Portfolios_Formed_on_BETA",
    "Portfolios_Formed_on_NI", "Portfolios_Formed_on_VAR", "Portfolios_Formed_on_RESVAR",
    "6_Portfolios_2x3", "6_Portfolios_ME_OP_2x3", "6_Portfolios_ME_INV_2x3",
    "6_Portfolios_ME_Prior_12_2", "10_Portfolios_Prior_12_2", "10_Portfolios_Prior_1_0",
    "10_Portfolios_Prior_60_13", "30_Industry_Portfolios", "30_Industry_Portfolios_daily",
    "49_Industry_Portfolios",
]
REGIONS = ["Developed", "Developed_ex_US", "Europe", "Japan", "Asia_Pacific_ex_Japan", "North_America"]
FRENCH_INTL = []
for _r in REGIONS:
    _mom = "MOM" if _r == "Asia_Pacific_ex_Japan" else "Mom"
    FRENCH_INTL += [f"{_r}_5_Factors", f"{_r}_{_mom}_Factor", f"{_r}_6_Portfolios_ME_BE-ME",
                    f"{_r}_6_Portfolios_ME_OP", f"{_r}_6_Portfolios_ME_INV",
                    f"{_r}_6_Portfolios_ME_Prior_12_2"]
FRENCH_INTL += ["Emerging_5_Factors", "Emerging_MOM_Factor", "Emerging_Markets_6_Portfolios_ME_BE-ME",
                "Emerging_Markets_6_Portfolios_ME_OP", "Emerging_Markets_6_Portfolios_ME_INV",
                "Emerging_Markets_6_Portfolios_ME_Prior_12_2"]
FRENCH_FILES = FRENCH_US + FRENCH_INTL

OSAP_SHA = "ad1dfba5a6d80c4ce53ce6b8127f5a949dda1e40"
OSAP_BASE = f"https://huggingface.co/datasets/OpenSourceAP/CrossSection/resolve/{OSAP_SHA}/"
# Hashes recorded by the archived study 2026-11-01-behavioral-benchmark (same snapshot).
OSAP_FILES = {
    "PredictorAltPorts_QuintilesVW.parquet": ("Portfolios/Full%20Sets%20Alt/PredictorAltPorts_QuintilesVW.parquet",
        "1c3f424e8b5839226d88b856daed888567f7e5d760a47fc4849ebc65ecd04c93"),
    "PredictorAltPorts_LiqScreen_ME_gt_NYSE20pct.parquet": ("Portfolios/Full%20Sets%20Alt/PredictorAltPorts_LiqScreen_ME_gt_NYSE20pct.parquet",
        "fcd2ae4053d7262868f5531be051ab6039161f7422091651116cf4a6990f3734"),
    "SignalDoc.csv": ("SignalDoc.csv", "0ceb11020c2138c2477b732948beaac2e67ccaad8428753e3a79af2bb5ea0178"),
}

# Yahoo: asset-class building blocks and benchmarks.
YAHOO_CORE = ["SPY", "VTI", "ACWI", "VT", "EFA", "EEM", "IWM", "AGG", "IEF", "TLT", "SHY", "BIL", "GLD",
              "DBC", "VNQ", "VFINX", "VGTSX", "VEIEX", "VBMFX", "VFITX", "VUSTX", "VGSIX", "VFISX",
              "EUNL.DE", "SXR8.DE", "VWCE.DE", "EXSA.DE"]
# Real factor products -> benchmark in the same currency (module C5).
ETF_PAIRS = {
    "SPY": ["MTUM", "PDP", "XMMO", "SPMO", "QMOM", "AMOMX",                 # momentum
            "QUAL", "SPHQ", "MOAT",                                          # quality
            "VLUE", "VTV", "IWD", "QVAL", "PRF", "FNDX", "COWZ", "SYLD", "PKW", "DFLVX",  # value / yield
            "USMV", "SPLV",                                                  # low volatility
            "SIZE", "IJR", "IWM", "VBR", "IJS", "AVUV", "DFSVX", "RSP",      # size / small value / equal weight
            "DVY", "SDY", "VIG", "SCHD", "NOBL",                             # dividends
            "AQMIX", "DBMF", "KMLM", "WTMF", "GMOM"],                        # trend / tactical
    "EFA": ["IMTM", "IMOM", "IQLT", "IVLU", "EFV", "EFAV", "SCZ", "IVAL"],
    "EUNL.DE": ["IS3R.DE", "XDEM.DE", "IS3Q.DE", "XDEQ.DE", "IS3S.DE", "XDEV.DE", "IQQ0.DE", "XDEB.DE",
                "IS3T.DE", "IUSN.DE", "ZPRV.DE", "ISPA.DE", "VGWD.DE", "TDIV.AS"],
}
ETF_GROUP = {}
for _g, _syms in {
    "Momentum": "MTUM PDP XMMO SPMO QMOM AMOMX IMTM IMOM IS3R.DE XDEM.DE",
    "Quality": "QUAL SPHQ MOAT IQLT IS3Q.DE XDEQ.DE",
    "Value": "VLUE VTV IWD QVAL PRF FNDX COWZ SYLD PKW DFLVX IVLU EFV IVAL IS3S.DE XDEV.DE",
    "Geringe Schwankung": "USMV SPLV EFAV IQQ0.DE XDEB.DE",
    "Nebenwerte": "SIZE IJR IWM VBR IJS AVUV DFSVX RSP SCZ IS3T.DE IUSN.DE ZPRV.DE",
    "Dividende": "DVY SDY VIG SCHD NOBL ISPA.DE VGWD.DE TDIV.AS",
    "Trend/Taktisch": "AQMIX DBMF KMLM WTMF GMOM",
}.items():
    for _s in _syms.split():
        ETF_GROUP[_s] = _g
YAHOO_SYMBOLS = sorted(set(YAHOO_CORE) | {s for v in ETF_PAIRS.values() for s in v} | set(ETF_PAIRS))

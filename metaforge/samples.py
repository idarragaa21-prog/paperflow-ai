"""Built-in example datasets and blank CSV templates."""
from __future__ import annotations

EXAMPLES: dict[str, dict] = {
    "doac_or": {
        "title": "DOACs vs warfarin — stroke/SE (OR, 2x2)",
        "favours_low": "DOAC",
        "favours_high": "warfarin",
        "csv": (
            "study_label,year,subgroup,effect_measure,a_events,b_non_events,c_events,d_non_events\n"
            "Connolly 2009 (RE-LY),2009,Thrombin inhibitor,OR,134,5973,199,5823\n"
            "Granger 2011 (ARISTOTLE),2011,Factor Xa,OR,212,8908,265,8795\n"
            "Patel 2011 (ROCKET-AF),2011,Factor Xa,OR,269,6989,306,6985\n"
            "Giugliano 2013 (ENGAGE),2013,Factor Xa,OR,296,6739,337,6695\n"
        ),
    },
    "statin_rr": {
        "title": "Statins — major vascular events (RR, 2x2)",
        "favours_low": "statin",
        "favours_high": "placebo",
        "csv": (
            "study_label,year,effect_measure,a_events,b_non_events,c_events,d_non_events\n"
            "4S 1994,1994,RR,431,1790,622,1592\n"
            "WOSCOPS 1995,1995,RR,174,2987,248,2911\n"
            "CARE 1996,1996,RR,212,1871,274,1804\n"
            "LIPID 1998,1998,RR,557,3995,715,3835\n"
            "HPS 2002,2002,RR,898,9366,1212,9119\n"
        ),
    },
    "smd": {
        "title": "Psychotherapy vs control — depression (SMD, arm summaries)",
        "favours_low": "therapy",
        "favours_high": "control",
        "csv": (
            "study_label,year,effect_measure,n_intervention,mean_intervention,sd_intervention,n_control,mean_control,sd_control\n"
            "Trial A,2015,SMD,40,18.2,6.1,38,22.5,6.4\n"
            "Trial B,2017,SMD,55,16.8,5.4,52,19.9,5.8\n"
            "Trial C,2018,SMD,30,20.1,7.0,31,21.0,7.2\n"
            "Trial D,2020,SMD,72,15.5,5.0,70,18.8,5.3\n"
        ),
    },
    "prevalence": {
        "title": "Disease prevalence (proportion, logit)",
        "favours_low": "",
        "favours_high": "",
        "csv": (
            "study_label,year,effect_measure,events,n_total\n"
            "Region A,2018,PLOGIT,42,512\n"
            "Region B,2019,PLOGIT,67,498\n"
            "Region C,2020,PLOGIT,38,605\n"
            "Region D,2021,PLOGIT,55,540\n"
        ),
    },
}

TEMPLATES: dict[str, str] = {
    "2x2": "study_label,year,subgroup,effect_measure,a_events,b_non_events,c_events,d_non_events\n",
    "person_time": "study_label,year,effect_measure,events_intervention,time_intervention,events_control,time_control\n",
    "continuous": "study_label,year,effect_measure,n_intervention,mean_intervention,sd_intervention,n_control,mean_control,sd_control\n",
    "proportion": "study_label,year,effect_measure,events,n_total\n",
    "correlation": "study_label,year,effect_measure,r,n_total\n",
    "precomputed": "study_label,year,effect_measure,effect_value,ci_lower_95,ci_upper_95\n",
    "generic": "study_label,year,effect_measure,yi,se\n",
}

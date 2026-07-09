import numpy as np


class FireSeasonIndices:
    """
    Fire season phenology module:
    - Onset
    - WinterOnset
    - Fire Season Length (FSL)
    - Winter Rain
    """

    # =========================================================
    # ONSET
    # =========================================================
    @staticmethod
    def calculate_onset(
        onset_method,
        snow_seuil,
        sd_cond_percent_ij,
        temp_seuil,
        t2m_ij,
        sd_ij,
    ):
        """
        Returns first valid fire season day index (1-based).
        """

        len_time = len(t2m_ij)

        # -------------------------
        # Temperature only
        # -------------------------
        if onset_method == "T":
            for nt in range(len_time - 2):
                if (
                    t2m_ij[nt] > temp_seuil
                    and t2m_ij[nt + 1] > temp_seuil
                    and t2m_ij[nt + 2] > temp_seuil
                ):
                    return nt + 3
            return np.nan

        # -------------------------
        # Temp + Snow (TS)
        # -------------------------
        if onset_method == "TS":
            use_snow = sd_cond_percent_ij >= 75.0

            for nt in range(len_time - 2):

                temp_ok = (
                    t2m_ij[nt] > temp_seuil
                    and t2m_ij[nt + 1] > temp_seuil
                    and t2m_ij[nt + 2] > temp_seuil
                )

                if use_snow:
                    snow_ok = (
                        sd_ij[nt] < snow_seuil
                        and sd_ij[nt + 1] < snow_seuil
                        and sd_ij[nt + 2] < snow_seuil
                    )
                else:
                    snow_ok = True

                if temp_ok and snow_ok:
                    return nt + 3

            return np.nan

        # -------------------------
        # TS0 (snow = 0 condition)
        # -------------------------
        if onset_method == "TS0":
            use_snow = sd_cond_percent_ij >= 75.0

            for nt in range(len_time - 2):

                temp_ok = (
                    t2m_ij[nt] > temp_seuil
                    and t2m_ij[nt + 1] > temp_seuil
                    and t2m_ij[nt + 2] > temp_seuil
                )

                if use_snow:
                    snow_ok = (
                        sd_ij[nt] == 0
                        and sd_ij[nt + 1] == 0
                        and sd_ij[nt + 2] == 0
                    )
                else:
                    snow_ok = True

                if temp_ok and snow_ok:
                    return nt + 3

            return np.nan

        # -------------------------
        # ToS (temperature OR snow)
        # -------------------------
        if onset_method == "ToS":
            use_snow = sd_cond_percent_ij >= 75.0

            for nt in range(len_time - 2):

                if use_snow:
                    if (
                        sd_ij[nt] == 0
                        and sd_ij[nt + 1] == 0
                        and sd_ij[nt + 2] == 0
                    ):
                        return nt + 3

                if (
                    t2m_ij[nt] > temp_seuil
                    and t2m_ij[nt + 1] > temp_seuil
                    and t2m_ij[nt + 2] > temp_seuil
                ):
                    return nt + 3

            return np.nan

        return np.nan

    # =========================================================
    # WINTER ONSET
    # =========================================================
    @staticmethod
    def calculate_winter_onset(
        t2m_ij,
        threshold=5.0,
        start_idx=240,
    ):
        """
        First persistent cold period indicating end of fire season.
        """

        for nt in range(start_idx, len(t2m_ij) - 2):
            if (
                t2m_ij[nt] < threshold
                and t2m_ij[nt + 1] < threshold
                and t2m_ij[nt + 2] < threshold
            ):
                return nt + 3

        return np.nan

    # =========================================================
    # FIRE SEASON LENGTH
    # =========================================================
    @staticmethod
    def calculate_fsl(onset_jd, winter_onset_jd):
        """
        Fire Season Length (days)
        """
        if np.isnan(onset_jd) or np.isnan(winter_onset_jd):
            return np.nan

        return winter_onset_jd - onset_jd

    # =========================================================
    # WINTER RAIN
    # =========================================================
    @staticmethod
    def calculate_winter_rain(
        dtp_cy_ij,
        dtp_py_ij,
        onset_jd,
        winter_onset_py_jd,
    ):
        """
        Precipitation memory used for DC initialization.

        - dtp_cy: current year precipitation
        - dtp_py: previous year precipitation
        """

        if np.isnan(onset_jd) or np.isnan(winter_onset_py_jd):
            return np.nan

        # precipitation before onset (current year)
        tp_cy = np.sum(dtp_cy_ij[: int(onset_jd) - 1])

        # precipitation after winter onset (previous year)
        tp_py = np.sum(dtp_py_ij[int(winter_onset_py_jd) - 1 :])

        return tp_cy + tp_py

    # =========================================================
    # OPTIONAL WRAPPER (recommended)
    # =========================================================
    @staticmethod
    def compute_all(
        t2m_ij,
        sd_ij,
        dtp_cy_ij,
        dtp_py_ij,
        sd_cond_percent_ij,
        onset_method,
        snow_seuil,
        temp_seuil,
        year=None,
    ):
        """
        Convenience function to compute all indices at once.
        """

        onset = FireSeasonIndices.calculate_onset(
            onset_method,
            snow_seuil,
            sd_cond_percent_ij,
            temp_seuil,
            t2m_ij,
            sd_ij,
        )

        winter_onset = FireSeasonIndices.calculate_winter_onset(t2m_ij)

        fsl = FireSeasonIndices.calculate_fsl(onset, winter_onset)
        
        if dtp_py_ij is None:
            winter_rain = np.nan
        else:
            winter_rain = FireSeasonIndices.calculate_winter_rain(
                dtp_cy_ij,
                dtp_py_ij,
                onset,
                winter_onset,
            )

        return {
            "Onset": onset,
            "WinterOnset": winter_onset,
            "FSL": fsl,
            "WinterRain": winter_rain,
        }
function [glacier_cost_per] = s3_glacier_per_month(volume, t)
    glacier_cost_per = t * volume * 1024 * 0.011;

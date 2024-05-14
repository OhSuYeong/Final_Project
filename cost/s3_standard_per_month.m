function [standard_cost_per] = s3_standard_per_month(volume, t)
    if volume <= (50*1024)
        standard_cost_per = t * volume * 1024 * 0.025;
    elseif (volume >= (450*1024)) && (volume < (500*1024))
        standard_cost_per = (t * 50 * 1024 * 0.025) + (t * (volume-50) * 1024 * 0.024);
    else
        standard_cost_per = (t * 50 * 1024 * 0.025) + (t * 450 * 1024 * 0.024) + (t * (volume-500) * 1024 * 0.023);
    end

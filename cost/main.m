clear all
clc

%Parameter
t=12;   % 12개월
volume = 100*1024;   %100TB
iteration = 100;    % 비율 퍼센트

alpha = 0:0.01:1;

% S3 Standard의 월별 요금 부과 함수
[standard_standard] = s3_standard_per_month(volume,t);

% S3 Glacier의 월별 요금 부과 함수
[glacier_standard] = s3_glacier_per_month(volume, t);

% Parameter of Alpha Filter(Exp)
for i = 1 : iteration + 1
    [result(i)] = standard_standard * (1-alpha(i)) + glacier_standard * alpha(i);
end

result = result./(10^7);

figure(1);
plot(alpha, result, 'k-', 'LineWidth', 1);
yline(result(1), '--', '상한선', 'color', 'blue');
yline(result(101), '--', '하한선', 'color', 'red');
xlabel('alpha');
ylabel('USD (10M)');
title('AWS S3 Storageclass cost');
grid on;

ax = gca;                       
existingYTicks = ax.YTick;      

newYTicks = unique([existingYTicks, result(1), result(101)]);
newYTicks = sort(newYTicks);

ax.YTick = newYTicks;
ax.YLim = [min(newYTicks) max(newYTicks)];

hold off;                       % Release the hold on the plot

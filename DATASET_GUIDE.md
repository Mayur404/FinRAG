# FinanceBench Minimum-Page Evaluation Guide (50 Questions / 882 Pages)

This document provides the definitive **least-possible-page configuration** from the **FinanceBench** benchmark dataset (Jimeno Yepes et al., 2024) to evaluate **exactly 50 questions**.

> **Mathematical Optimization:** Across all 84 documents in FinanceBench, this 18-document subset achieves the global minimum volume of **882 total pages** (average of only **17.6 pages per question**), eliminating all heavy 300+ and 500+ page filings while retaining maximum evaluation coverage.

## 1. Document Overview (Sorted by Page Count Ascending)

| # | Document Name | Questions | Pages | Company | Filing Type | Reporting Period |
| :-: | :--- | :-: | :-: | :--- | :--- | :--- |
| 1 | FOOTLOCKER_2022_8K_dated-2022-05-20.pdf | **1** | 4 | Foot Locker | 8-K Current Report | May 2022 |
| 2 | PEPSICO_2023_8K_dated-2023-05-05.pdf | **1** | 5 | PepsiCo | 8-K Current Report | May 2023 |
| 3 | AMCOR_2022_8K_dated-2022-07-01.pdf | **1** | 9 | Amcor | 8-K Current Report | July 2022 |
| 4 | ULTABEAUTY_2023Q4_EARNINGS.pdf | **4** | 9 | Ulta Beauty | Earnings Release | FY2023 Q4 |
| 5 | AMCOR_2023Q4_EARNINGS.pdf | **2** | 14 | Amcor | Earnings Release | FY2023 Q4 |
| 6 | MGMRESORTS_2022Q4_EARNINGS.pdf | **3** | 15 | MGM Resorts | Earnings Release | FY2022 Q4 |
| 7 | PEPSICO_2023Q1_EARNINGS.pdf | **2** | 16 | PepsiCo | Earnings Release | FY2023 Q1 |
| 8 | JOHNSON_JOHNSON_2022Q4_EARNINGS.pdf | **2** | 24 | Johnson & Johnson | Earnings Release | FY2022 Q4 |
| 9 | JOHNSON_JOHNSON_2023Q2_EARNINGS.pdf | **1** | 24 | Johnson & Johnson | Earnings Release | FY2023 Q2 |
| 10 | JOHNSON_JOHNSON_2023_8K_dated-2023-08-30.pdf | **3** | 27 | Johnson & Johnson | 8-K Current Report | August 2023 |
| 11 | BESTBUY_2024Q2_10Q.pdf | **3** | 30 | Best Buy | 10-Q Quarterly Report | FY2024 Q2 |
| 12 | FOOTLOCKER_2022_8K_dated_2022-08-19.pdf | **1** | 31 | Foot Locker | 8-K Current Report | August 2022 |
| 13 | Pfizer_2023Q2_10Q.pdf | **3** | 72 | Pfizer | 10-Q Quarterly Report | FY2023 Q2 |
| 14 | BESTBUY_2023_10K.pdf | **3** | 75 | Best Buy | 10-K Annual Report | FY2023 |
| 15 | 3M_2023Q2_10Q.pdf | **3** | 92 | 3M | 10-Q Quarterly Report | FY2023 Q2 |
| 16 | AMD_2022_10K.pdf | **7** | 121 | AMD | 10-K Annual Report | FY2022 |
| 17 | VERIZON_2022_10K.pdf | **3** | 124 | Verizon | 10-K Annual Report | FY2022 |
| 18 | BOEING_2022_10K.pdf | **7** | 190 | Boeing | 10-K Annual Report | FY2022 |
| **Total** | **18 Documents** | **50** | **882** | - | - | - |

---

## 2. Structured Questions and Gold Standard Answers

### 1. FOOTLOCKER_2022_8K_dated-2022-05-20.pdf (1 Questions, 4 Pages)

#### Question 1: Were there any board member nominees who had substantially more votes against joining than the other nominees?
- **FinanceBench ID:** financebench_id_00822
- **Question Type:** novel-generated
- **Target Document:** FOOTLOCKER_2022_8K_dated-2022-05-20.pdf (Page 1)
- **Expected Answer:**
  > Yes, his name is Richard A. Johnson
- **Evidence / Ground Truth Justification:**
  > Richard A. Johnson had roughly 16.1 million votes against him joining whereas the maximum votes against joining among all other candidates was roughly 6.1 million.

### 2. PEPSICO_2023_8K_dated-2023-05-05.pdf (1 Questions, 5 Pages)

#### Question 2: At the Pepsico AGM held on May 3, 2023, what was the outcome of the shareholder vote on the shareholder proposal for a congruency report by Pepsico on net-zero emissions policies?
- **FinanceBench ID:** financebench_id_01482
- **Question Type:** novel-generated
- **Target Document:** PEPSICO_2023_8K_dated-2023-05-05.pdf (Page 3)
- **Expected Answer:**
  > The shareholder proposal for a congruency report by Pepsico on net-zero emissions policies was defeated.

### 3. AMCOR_2022_8K_dated-2022-07-01.pdf (1 Questions, 9 Pages)

#### Question 3: What was the key agenda of the AMCOR's 8k filing dated 1st July 2022?
- **FinanceBench ID:** financebench_id_01935
- **Question Type:** novel-generated
- **Target Document:** AMCOR_2022_8K_dated-2022-07-01.pdf (Page 1)
- **Expected Answer:**
  > Amcor Finance (USA), Inc. and Amcor Flexibles North America, Inc., entered into supplemental indentures relating to Guaranteed Senior Notes due 2026 and 2028. This involved the substitution of the Substitute Issuer (Amcor Flexibles North America) for the Former Issuer (Amcor Finance) and the assumption of covenants under the indentures. (In essence a novation agreement)

### 4. ULTABEAUTY_2023Q4_EARNINGS.pdf (4 Questions, 9 Pages)

#### Question 4: What drove the reduction in SG&A expense as a percent of net sales in FY2023?
- **FinanceBench ID:** financebench_id_00601
- **Question Type:** novel-generated
- **Target Document:** ULTABEAUTY_2023Q4_EARNINGS.pdf (Page 1)
- **Expected Answer:**
  > Lower marketing expenses and leverage of incentive compensation due to higher sales. The answer here assumes FY2023 refers to the 12 months ended on January 28, 2023 (although the company refers to this period as its fiscal 2022.
- **Evidence / Ground Truth Justification:**
  > Fiscal 2022 = FY2023. Fiscal 2021 = FY2022.

#### Question 5: What drove the increase in Ulta Beauty's merchandise inventories balance at end of FY2023?
- **FinanceBench ID:** financebench_id_00603
- **Question Type:** novel-generated
- **Target Document:** ULTABEAUTY_2023Q4_EARNINGS.pdf (Page 2)
- **Expected Answer:**
  > Increase in Merchandise inventories balance was driven by the opening of 47 new stores. The answer here assumes FY2023 refers to the 12 months ended on January 28, 2023 (although the company refers to this period as its fiscal 2022.
- **Evidence / Ground Truth Justification:**
  > Fiscal 2022 = FY2023. Fiscal 2021 = FY2022.

#### Question 6: What percent of Ulta Beauty's total spend on stock repurchases for FY 2023 occurred in Q4 of FY2023?
- **FinanceBench ID:** financebench_id_00605
- **Question Type:** novel-generated
- **Target Document:** ULTABEAUTY_2023Q4_EARNINGS.pdf (Page 2)
- **Expected Answer:**
  > 36%. The answer here assumes FY2023 refers to the 12 months ended on January 28, 2023 (although the company refers to this period as its fiscal 2022.
- **Evidence / Ground Truth Justification:**
  > Fiscal 2022 = FY2023. Fiscal 2021 = FY2022. Percent spent in Q4 of FY2023 = Amount spent in Q4 of FY2023/Total amount spent in FY2023*100 =$328.1 million /$900 million * 100 = 36%

#### Question 7: Did Ulta Beauty's wages expense as a percent of net sales increase or decrease in FY2023?
- **FinanceBench ID:** financebench_id_00606
- **Question Type:** novel-generated
- **Target Document:** ULTABEAUTY_2023Q4_EARNINGS.pdf (Page 1)
- **Expected Answer:**
  > Wages expense as a percent of net sales increased in FY2023. The answer here assumes FY2023 refers to the 12 months ended on January 28, 2023 (although the company refers to this period as its fiscal 2022.
- **Evidence / Ground Truth Justification:**
  > Fiscal 2022 = FY2023. Fiscal 2021 = FY2022. Store payroll and benefits = wages. Store payroll and benefits offsets reduction in SG&A percent of net sales in FY2023.

### 5. AMCOR_2023Q4_EARNINGS.pdf (2 Questions, 14 Pages)

#### Question 8: What Was AMCOR's Adjusted Non GAAP EBITDA for FY 2023
- **FinanceBench ID:** financebench_id_01928
- **Question Type:** novel-generated
- **Target Document:** AMCOR_2023Q4_EARNINGS.pdf (Page 11)
- **Expected Answer:**
  > AMCOR's Adj. EBITDA was $2,018mn in FY 2023

#### Question 9: How much was the Real change in Sales for AMCOR in FY 2023 vs FY 2022, if we exclude the impact of FX movement, passthrough costs and one-off items?
- **FinanceBench ID:** financebench_id_01930
- **Question Type:** novel-generated
- **Target Document:** AMCOR_2023Q4_EARNINGS.pdf (Page 9)
- **Expected Answer:**
  > The Real Growth was flat in FY 2023 vs FY 2022.

### 6. MGMRESORTS_2022Q4_EARNINGS.pdf (3 Questions, 15 Pages)

#### Question 10: Which region had the Highest EBITDAR Contribution for MGM during FY2022?
- **FinanceBench ID:** financebench_id_00382
- **Question Type:** novel-generated
- **Target Document:** MGMRESORTS_2022Q4_EARNINGS.pdf (Page 12)
- **Expected Answer:**
  > Las Vegas resorts contributed ~90% of company level EBITDAR during FY2022.
- **Evidence / Ground Truth Justification:**
  > 3142308/3497254

#### Question 11: What was MGM's interest coverage ratio using FY2022 Adjusted EBIT as the numerator and annual Interest Expense as the denominator?
- **FinanceBench ID:** financebench_id_01911
- **Question Type:** novel-generated
- **Target Document:** MGMRESORTS_2022Q4_EARNINGS.pdf (Page 13)
- **Expected Answer:**
  > As adjusted EBIT is negative, coverage ratio is zero

#### Question 12: Which region had the worst topline performance for MGM during FY2022?
- **FinanceBench ID:** financebench_id_01912
- **Question Type:** novel-generated
- **Target Document:** MGMRESORTS_2022Q4_EARNINGS.pdf (Page 2, 3, 3)
- **Expected Answer:**
  > MGM China experienced the worst topline performance amongst the other regions presented. Its revenue declined 44% in FY2022 whereas the other regions presented increased their revenues.

### 7. PEPSICO_2023Q1_EARNINGS.pdf (2 Questions, 16 Pages)

#### Question 13: As of FY2023Q1, why did Pepsico raise full year guidance for FY2023?
- **FinanceBench ID:** financebench_id_01474
- **Question Type:** novel-generated
- **Target Document:** PEPSICO_2023Q1_EARNINGS.pdf (Page 0)
- **Expected Answer:**
  > Pepsico experienced a strong start to FY2023.

#### Question 14: As of FY2023Q1, by how many percentage points did Pepsico raise full year guidance in respect of core constant currency EPS growth?
- **FinanceBench ID:** financebench_id_01476
- **Question Type:** novel-generated
- **Target Document:** PEPSICO_2023Q1_EARNINGS.pdf (Page 0)
- **Expected Answer:**
  > Pepsico raised full year guidance in respect of core constant currency EPS growth by 1 percentage point.

### 8. JOHNSON_JOHNSON_2022Q4_EARNINGS.pdf (2 Questions, 24 Pages)

#### Question 15: Is growth in JnJ's adjusted EPS expected to accelerate in FY2023?
- **FinanceBench ID:** financebench_id_00651
- **Question Type:** novel-generated
- **Target Document:** JOHNSON_JOHNSON_2022Q4_EARNINGS.pdf (Page 0)
- **Expected Answer:**
  > No, rate of growth in adjusted EPS is expected to decelerate slightly from 3.6% in FY2022 to 3.5% in FY2023.
- **Evidence / Ground Truth Justification:**
  > FY2023 adjusted EPS growth of 3.5% is slightly lower than FY2022 adjusted EPS growth of 3.6%.

#### Question 16: How did JnJ's US sales growth compare to international sales growth in FY2022?
- **FinanceBench ID:** financebench_id_01484
- **Question Type:** novel-generated
- **Target Document:** JOHNSON_JOHNSON_2022Q4_EARNINGS.pdf (Page 1)
- **Expected Answer:**
  > US sales increased 3.0% vs international sales decline of 0.6%.

### 9. JOHNSON_JOHNSON_2023Q2_EARNINGS.pdf (1 Questions, 24 Pages)

#### Question 17: Did JnJ's net earnings as a percent of sales increase in Q2 of FY2023 compared to Q2 of FY2022?
- **FinanceBench ID:** financebench_id_01487
- **Question Type:** novel-generated
- **Target Document:** JOHNSON_JOHNSON_2023Q2_EARNINGS.pdf (Page 9)
- **Expected Answer:**
  > Yes, net earnings as a percent of sales increased from 20% in Q2 of FY2022 to 20.1% in Q2 of FY2023.

### 10. JOHNSON_JOHNSON_2023_8K_dated-2023-08-30.pdf (3 Questions, 27 Pages)

#### Question 18: Which business segment of JnJ will be treated as a discontinued operation from August 30, 2023 onward?
- **FinanceBench ID:** financebench_id_01488
- **Question Type:** novel-generated
- **Target Document:** JOHNSON_JOHNSON_2023_8K_dated-2023-08-30.pdf (Page 3)
- **Expected Answer:**
  > The Consumer Health business segment will be treated as a discontinued operation from August 30, 2023 onward.

#### Question 19: What is the amount of the gain accruing to JnJ as a result of the separation of its Consumer Health business segment, as of August 30, 2023?
- **FinanceBench ID:** financebench_id_01490
- **Question Type:** novel-generated
- **Target Document:** JOHNSON_JOHNSON_2023_8K_dated-2023-08-30.pdf (Page 3)
- **Expected Answer:**
  > JnJ will make a gain of approximately $20 billion from the separation of its Consumer Health business segment.

#### Question 20: What is the amount of the cash proceeds that JnJ realised from the separation of Kenvue (formerly Consumer Health business segment), as of August 30, 2023?
- **FinanceBench ID:** financebench_id_01491
- **Question Type:** novel-generated
- **Target Document:** JOHNSON_JOHNSON_2023_8K_dated-2023-08-30.pdf (Page 3)
- **Expected Answer:**
  > JnJ realised $13.2 billion in cash proceeds from the separation of Kenvue.

### 11. BESTBUY_2024Q2_10Q.pdf (3 Questions, 30 Pages)

#### Question 21: Was there any drop in Cash & Cash equivalents between FY 2023 and Q2 of FY2024?
- **FinanceBench ID:** financebench_id_00288
- **Question Type:** novel-generated
- **Target Document:** BESTBUY_2024Q2_10Q.pdf (Page 19)
- **Expected Answer:**
  > Yes, there was a decline of ~42% between FY2023 and Q2 of FY 2024.
- **Evidence / Ground Truth Justification:**
  > 1093/1874-1

#### Question 22: Was there any change in the number of Best Buy stores between Q2 of FY2024 and FY2023?
- **FinanceBench ID:** financebench_id_00460
- **Question Type:** novel-generated
- **Target Document:** BESTBUY_2024Q2_10Q.pdf (Page 16)
- **Expected Answer:**
  > Yes, there is decline in number stores by 1.32% from 982 stores in Q2 FY 2023 to 969 by the end of Q2 FY2024.
- **Evidence / Ground Truth Justification:**
  > 969/982-1

#### Question 23: Which Best Buy product category performed the best (by top line) in the domestic (USA) Market during Q2 of FY2024?
- **FinanceBench ID:** financebench_id_01902
- **Question Type:** novel-generated
- **Target Document:** BESTBUY_2024Q2_10Q.pdf (Page 17)
- **Expected Answer:**
  > The entertainment segment experienced the highest growth of 9% during Q2 FY2024, primarily from gaming division.

### 12. FOOTLOCKER_2022_8K_dated_2022-08-19.pdf (1 Questions, 31 Pages)

#### Question 24: Does Foot Locker's new CEO have previous CEO experience in a similar company to Footlocker?
- **FinanceBench ID:** financebench_id_00839
- **Question Type:** novel-generated
- **Target Document:** FOOTLOCKER_2022_8K_dated_2022-08-19.pdf (Page 1)
- **Expected Answer:**
  > Yes. She was previous CEO of Ulta Beauty which means she had to manage a large retail company that has brick and mortar + online business. So yes she was a CEO in a similar company to Foot Locker before this.

### 13. Pfizer_2023Q2_10Q.pdf (3 Questions, 72 Pages)

#### Question 25: How much does Pfizer expect to pay to spin off Upjohn in the future in USD million?
- **FinanceBench ID:** financebench_id_00283
- **Question Type:** novel-generated
- **Target Document:** Pfizer_2023Q2_10Q.pdf (Page 40)
- **Expected Answer:**
  > 77.78
- **Evidence / Ground Truth Justification:**
  > 10% cost is remaining amount in the future. Calculation: 700/9 is 10% of the cost remaining

#### Question 26: For Pfizer, which geographic region had the biggest drop in Q22023 year over year revenues (on a percentage basis)?
- **FinanceBench ID:** financebench_id_00724
- **Question Type:** novel-generated
- **Target Document:** Pfizer_2023Q2_10Q.pdf (Page 37)
- **Expected Answer:**
  > Developed Rest of the World
- **Evidence / Ground Truth Justification:**
  > It's plainly stated in table format the year over year revenue changes for each of the regions

#### Question 27: As of Q2'2023, is Pfizer spinning off any large business segments?
- **FinanceBench ID:** financebench_id_02419
- **Question Type:** novel-generated
- **Target Document:** Pfizer_2023Q2_10Q.pdf (Page 40)
- **Expected Answer:**
  > Yes, it's spinning off Upjohn.

### 14. BESTBUY_2023_10K.pdf (3 Questions, 75 Pages)

#### Question 28: Are Best Buy's gross margins historically consistent (not fluctuating more than roughly 2% each year)? If gross margins are not a relevant metric for a company like this, then please state that and explain why.
- **FinanceBench ID:** financebench_id_00685
- **Question Type:** domain-relevant
- **Target Document:** BESTBUY_2023_10K.pdf (Page 39)
- **Expected Answer:**
  > Yes, the margins have been consistent, there has been a minor decline of 1.1% in gross margins between FY2022 and FY2023.
- **Evidence / Ground Truth Justification:**
  > Gross Profit/Revenue
9912/46298
11640/51761

#### Question 29: What are major acquisitions that Best Buy has done in FY2023, FY2022 and FY2021?
- **FinanceBench ID:** financebench_id_01077
- **Question Type:** domain-relevant
- **Target Document:** BESTBUY_2023_10K.pdf (Page 50)
- **Expected Answer:**
  > Best Buy closed two acquisitions, both these companies were already partially owned by Best Buy, but Best Buy acquired all outstanding shares of these two companies during FY 2022: (1) Current Health Ltd and (2) Two Peaks, LLC d/b/a Yardbird Furniture

#### Question 30: Among operations, investing, and financing activities, which brought in the most (or lost the least) cash flow for Best Buy in FY2023?
- **FinanceBench ID:** financebench_id_01275
- **Question Type:** domain-relevant
- **Target Document:** BESTBUY_2023_10K.pdf (Page 41)
- **Expected Answer:**
  > Best Buy generated the most cash flow from operating activities in FY 2023 ($1.8 bn)

### 15. 3M_2023Q2_10Q.pdf (3 Questions, 92 Pages)

#### Question 31: Does 3M have a reasonably healthy liquidity profile based on its quick ratio for Q2 of FY2023? If the quick ratio is not relevant to measure liquidity, please state that and explain why.
- **FinanceBench ID:** financebench_id_00807
- **Question Type:** domain-relevant
- **Target Document:** 3M_2023Q2_10Q.pdf (Page 4)
- **Expected Answer:**
  > No. The quick ratio for 3M was 0.96 by Jun'23 close, which needs a bit of an improvement to touch the 1x mark
- **Evidence / Ground Truth Justification:**
  > Quick Ratio= (Total current assets-Total inventories)/Total current liabilities
(15,754-5,280)/10,936

#### Question 32: Which debt securities are registered to trade on a national securities exchange under 3M's name as of Q2 of 2023?
- **FinanceBench ID:** financebench_id_00941
- **Question Type:** domain-relevant
- **Target Document:** 3M_2023Q2_10Q.pdf (Page 0)
- **Expected Answer:**
  > Following debt securities registered under 3M's name are listed to trade on the New York Stock Exchange:
-1.500% Notes due 2026 (Trading Symbol: MMM26)
-1.750% Notes due 2030 (Trading Symbol: MMM30)
-1.500% Notes due 2031 (Trading Symbol: MMM31)

#### Question 33: Does 3M maintain a stable trend of dividend distribution?
- **FinanceBench ID:** financebench_id_01858
- **Question Type:** novel-generated
- **Target Document:** 3M_2023Q2_10Q.pdf (Page 61)
- **Expected Answer:**
  > Yes, not only they distribute the dividends on a routine basis, 3M has also been increasing the per share dividend for consecutive 65 years

### 16. AMD_2022_10K.pdf (7 Questions, 121 Pages)

#### Question 34: Does AMD have a reasonably healthy liquidity profile based on its quick ratio for FY22? If the quick ratio is not relevant to measure liquidity, please state that and explain why.
- **FinanceBench ID:** financebench_id_00222
- **Question Type:** domain-relevant
- **Target Document:** AMD_2022_10K.pdf (Page 55)
- **Expected Answer:**
  > Yes. The quick ratio is 1.57, calculated as (cash and cash equivalents+Short term investments+Accounts receivable, net+receivables from related parties)/ (current liabilities).

#### Question 35: What are the major products and services that AMD sells as of FY22?
- **FinanceBench ID:** financebench_id_00995
- **Question Type:** domain-relevant
- **Target Document:** AMD_2022_10K.pdf (Page 3)
- **Expected Answer:**
  > AMD sells server microprocessors (CPUs) and graphics processing units (GPUs), data processing units (DPUs), Field Programmable Gate Arrays (FPGAs), and Adaptive System-on-Chip (SoC) products for data centers; CPUs, accelerated processing units (APUs) that integrate CPUs and GPUs, and chipsets for desktop and notebook personal computers; discrete GPUs, and semi-custom SoC products and development services; and embedded CPUs, GPUs, APUs, FPGAs, and Adaptive SoC products.

#### Question 36: What drove revenue change as of the FY22 for AMD?
- **FinanceBench ID:** financebench_id_01198
- **Question Type:** domain-relevant
- **Target Document:** AMD_2022_10K.pdf (Page 42)
- **Expected Answer:**
  > In 2022, AMD reported Higher sales of their EPYC server processors, higher semi-custom product sales, and the inclusion of Xilinx embedded product sales

#### Question 37: What drove operating margin change as of the FY22 for AMD? If operating margin is not a useful metric for a company like this, then please state that and explain why.
- **FinanceBench ID:** financebench_id_00917
- **Question Type:** domain-relevant
- **Target Document:** AMD_2022_10K.pdf (Page 42)
- **Expected Answer:**
  > The decrease in AMD's operating income was primarily driven by amortization of intangible assets associated with the Xilinx acquisition

#### Question 38: Among operations, investing, and financing activities, which brought in the most (or lost the least) cash flow for AMD in FY22?
- **FinanceBench ID:** financebench_id_01279
- **Question Type:** domain-relevant
- **Target Document:** AMD_2022_10K.pdf (Page 57)
- **Expected Answer:**
  > In 2022, AMD brought in the most cashflow from Operations

#### Question 39: From FY21 to FY22, excluding Embedded, in which AMD reporting segment did sales proportionally increase the most?
- **FinanceBench ID:** financebench_id_00563
- **Question Type:** novel-generated
- **Target Document:** AMD_2022_10K.pdf (Page 47)
- **Expected Answer:**
  > Data Center
- **Evidence / Ground Truth Justification:**
  > Data center: 
FY22: 6,043
FY21: 3,694 
6,043/3,694-1 = 63,59%

Client: 
FY22: 6,201
FY21: 6,887 
6,201/6,887-1 = -9,96%


Gaming: 
FY22: 6,805
FY21: 5,607 
6,805/5,607-1 = 21,37%

#### Question 40: Did AMD report customer concentration in FY22?
- **FinanceBench ID:** financebench_id_00757
- **Question Type:** novel-generated
- **Target Document:** AMD_2022_10K.pdf (Page 11)
- **Expected Answer:**
  > Yes, one customer accounted for 16% of consolidated net revenue
- **Evidence / Ground Truth Justification:**
  > One customer ccounting for 16% of net evenue is a high customer concenration

### 17. VERIZON_2022_10K.pdf (3 Questions, 124 Pages)

#### Question 41: Does Verizon have a reasonably healthy liquidity profile based on its quick ratio for FY 2022? If the quick ratio is not relevant to measure liquidity, please state that and explain why.
- **FinanceBench ID:** financebench_id_00216
- **Question Type:** domain-relevant
- **Target Document:** VERIZON_2022_10K.pdf (Page 55)
- **Expected Answer:**
  > No. The quick ratio was approximately 0.54 for Verizon. It indicated that Verizon does not have a healthy liquidity profile.
- **Evidence / Ground Truth Justification:**
  > Quick ratio = (current assets - inventories - prepaid expenses) / current liabilities = (37857 - 2388 - 8358) / 50171 = 0.5403719

#### Question 42: Is Verizon a capital intensive business based on FY 2022 data?
- **FinanceBench ID:** financebench_id_00215
- **Question Type:** domain-relevant
- **Target Document:** VERIZON_2022_10K.pdf (Page 55, 22)
- **Expected Answer:**
  > Yes. Verizon's capital intensity ratio was approximately 2.774729. This means that it took approximately $2.77 of assets to generate $1 of revenue and thus, Verizon can be considered capital intensive.
- **Evidence / Ground Truth Justification:**
  > capital intensity ratio = total asset / revenue = 379680/ 136835 = 2.774729, which is relatively high

#### Question 43: Has Verizon increased its debt on balance sheet between 2022 and the 2021 fiscal period?
- **FinanceBench ID:** financebench_id_00566
- **Question Type:** domain-relevant
- **Target Document:** VERIZON_2022_10K.pdf (Page 76)
- **Expected Answer:**
  > No. Verizon's debt decreased by $229 million.
- **Evidence / Ground Truth Justification:**
  > debt change = debt in 2022 - debt in 2021 = 150639 - 150868 = -229

### 18. BOEING_2022_10K.pdf (7 Questions, 190 Pages)

#### Question 44: Are there any product categories / service categories that represent more than 20% of Boeing's revenue for FY2022?
- **FinanceBench ID:** financebench_id_00517
- **Question Type:** domain-relevant
- **Target Document:** BOEING_2022_10K.pdf (Page 61)
- **Expected Answer:**
  > Yes. Boeing has product and service categories that represent more than 20% of Boeing's revenue for FY2022. These categories are Commercial Airplanes which comprises 39% of total revenue, Defence which comprises 35% of total revenue and Services which comprises 26% of total revenue.
- **Evidence / Ground Truth Justification:**
  > Commercial Airplanes%=Revenues: Commercial Airplanes/Total revenues*100=25,867/66,608*100=39%. Defence%=Defense, Space & Security/Total revenues*100=23,162/66,608*100=35%. Services%=Global Services/Total revenues*100=17,611/66,608*100=26%.

#### Question 45: Has Boeing reported any materially important ongoing legal battles from FY2022?
- **FinanceBench ID:** financebench_id_01091
- **Question Type:** domain-relevant
- **Target Document:** BOEING_2022_10K.pdf (Page 112)
- **Expected Answer:**
  > Yes. Multiple lawsuits have been filed against Boeing resulting from a 2018 Lion Air crash and a 2019 Ethiopian Airlines crash.

#### Question 46: Does Boeing have an improving gross margin profile as of FY2022? If gross margin is not a useful metric for a company like this, then state that and explain why.
- **FinanceBench ID:** financebench_id_00678
- **Question Type:** domain-relevant
- **Target Document:** BOEING_2022_10K.pdf (Page 54)
- **Expected Answer:**
  > Yes. Boeing has an improving gross margin profile as of FY2022. Gross profit improved from $3,017 million in FY2021 to $3,502 million in FY2022. Gross margin % improved from 4.8% in FY2021 to 5.3% in FY2022.
- **Evidence / Ground Truth Justification:**
  > Gross margin%=Gross margin/Total revenues*100=3,502/66,608*100=5.3% for 2022 and 3,017/62,286*100=4.8% for 2021.

#### Question 47: Who are the primary customers of Boeing as of FY2022?
- **FinanceBench ID:** financebench_id_01290
- **Question Type:** domain-relevant
- **Target Document:** BOEING_2022_10K.pdf (Page 7, 9, 13)
- **Expected Answer:**
  > Boeing's primary customers as of FY2022 are a limited number of commercial airlines and the US government. The US government accounted for 40% of Boeing's total revenues in FY2022.

#### Question 48: Is Boeing's business subject to cyclicality?
- **FinanceBench ID:** financebench_id_00464
- **Question Type:** novel-generated
- **Target Document:** BOEING_2022_10K.pdf (Page 7)
- **Expected Answer:**
  > Yes, Boeing's business is subject to cyclicality due to its exposure to the airline industry which is a cyclical industry.
- **Evidence / Ground Truth Justification:**
  > A major portion of Boeing's revenue is derived from the sale of aircraft to commercial airlines. The commercial airlines business is cyclical, and subject to significant profit swings.

#### Question 49: What production rate changes is Boeing forecasting for FY2023?
- **FinanceBench ID:** financebench_id_00494
- **Question Type:** novel-generated
- **Target Document:** BOEING_2022_10K.pdf (Page 8)
- **Expected Answer:**
  > Boeing forecasts an increase in the production rates for the 737, 777X and 787 aircrafts in 2023.
- **Evidence / Ground Truth Justification:**
  > Boeing plans to gradually increase production rates for the 737 and 787 and to resume production of 777X.

#### Question 50: How does Boeing's effective tax rate in FY2022 compare to FY2021?
- **FinanceBench ID:** financebench_id_00585
- **Question Type:** novel-generated
- **Target Document:** BOEING_2022_10K.pdf (Page 54)
- **Expected Answer:**
  > Effective tax rate in FY2022 was 0.62%, compared to  -14.76% in FY2021.
- **Evidence / Ground Truth Justification:**
  > Effective tax rate=Income tax (expense) benefit/ Loss before income taxes*100=(31)/(5,022)*100=0.62% in 2022 and 743/(5,033)*100=-14.76%.

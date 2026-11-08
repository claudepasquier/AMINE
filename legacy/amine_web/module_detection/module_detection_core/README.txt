To ensure reproductibility, one has to set environment variable PYTHONHASHSEED to an integer value (the seed) :
export PYTHONHASHSEED=1
and to run the program on only one thread (set workers = 1 in models.py)

increase nb repeat in monte carlo simulation 10000
use all nodes as seed vs use only 10%

shell :
1 score sans correction, correction avec module connecté à la fin => essai1.txt
2
3 : correction avec module connecté full => essai3.txt
    178 minutes 215 modules < 0.05
4 : correction avec module non connecté puis avec module connecté à la fin => essai4.txt
    identique à précédemment avec juste la pvalue qui change
    168 minutes 55 modules < 0.05
5 : comme essai 4 mais avec coexpression >= 1 (mais résultats différents)
    383 modules, 55 modules < 0.05
6 : shBLIMP1 normoxia avec coexpression >= 1
    399 modules mais aucun avec pvalue < 0.05
7 : shBLIMP1 hypoxia avec coexpression >= 1
    507 modules mais aucun avec pvalue < 0.05
=> le mieux semble être la stratégie full
8  : BALF full avec coexpression >= 0
     536 annotations, 213 avec pvalue < 0.05
9  : normoxia full avec coexpression >= 0
     663 annotations mais 9 avec pvalue < 0.05
10 : hypoxia mais full avec coexpression >= 0
     709 annotations mais 0 avec pvalue < 0.05

11 : BALF full avec coexpression >= 1
     522 annotations, 46 avec pvalue < 0.05
12 : normoxia full avec coexpression >= 1
     608 annotations mais 0 avec pvalue < 0.05
13 : hypoxia full avec coexpression >= 1
     674 annotations mais 0 avec pvalue < 0.05
14 : BALF full avec coexpression >= 1 & weight = 1
     522 annotations, 38 avec pvalue < 0.05
15 : normoxia full avec coexpression >= 1 & weight = 1
     608 annotations mais 0 avec pvalue < 0.05
16 : hypoxia full avec coexpression >= 1 & weight = 1
     674 annotations mais 0 avec pvalue < 0.05

17 : BALF full avec coexpression >= 0 & ( weight = 1 ou weight = 'combined_score')
     546 annotations, 233 avec pvalue < 0.05
18 : normoxia full avec coexpression >= 0 &  ( weight = 1 ou weight = 'combined_score')
     668 annotations mais 9 avec pvalue < 0.05
19 : hypoxia full avec coexpression >= 0 &  ( weight = 1 ou weight = 'combined_score')
     707 annotations mais 0 avec pvalue < 0.05

20 : BALF full avec coexpression >= 0 & weight = 1, recalculation of pvalues at the end
     546 annotations, 109 avec pvalue < 0.05
21 : normoxia full avec coexpression >= 0 & weight = 1, recalculation of pvalues at the end
     668 annotations mais 2 avec pvalue < 0.05
22 : hypoxia full avec coexpression >= 0 & weight = 1, recalculation of pvalues at the end
     707 annotations mais 0 avec pvalue < 0.05

     23 : normoxia_likehood.csv
          671 annotations, 4 avec pvalue < 0.05
     24 : normoxia_moderated
          668 annotations mais 9 avec pvalue < 0.05
     25 : hypoxia_likehood
          733 annotations mais 0 avec pvalue < 0.05
     26 : hypoxia_moderated
          668 annotations mais 9 avec pvalue < 0.05
     27 : Hmga2
          705 annotations mais 19 avec pvalue < 0.05
     28 : Hmga2_likehood
          721 annotations mais 5 avec pvalue < 0.05
     29 : Hmga2_moderated
          706 annotations mais 19 avec pvalue < 0.05


TODO déterminer ce qui est préférable : coexpression >=1 ou coexpression >= 0 ::: coexpression==0
TODO 8 vérifier l'obtention des mêmes résultats que essai 4 (avec coexpression ==0)

Stouffer–Liptak–Kechris correction
https://academic.oup.com/bioinformatics/article/28/22/2986/240603

10/06/2020
essai modules overlappants

02/11/2020
test positive/negative avec pvalue, andienne version minscore=999 ; résultats dans blimp1_999

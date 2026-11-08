if("dplyr" %in% rownames(installed.packages()) == FALSE) {
  cat("\nInstalling dplyr R package...\n")
  install.packages("dplyr")
}
if("magrittr" %in% rownames(installed.packages()) == FALSE) {
  cat("\nInstalling magrittr R package...\n")
  install.packages("magrittr")
}
if("igraph" %in% rownames(installed.packages()) == FALSE) {
  cat("\nInstalling igraph R package...\n")
  install.packages("igraph")
}

args <- commandArgs(trailingOnly = TRUE)

if("--help" %in% args){
  system("clear")
  cat('\nPARAMETER OPTIONS:\n')
  cat('\n -f: Directory containing simulated networks. Each network is represented by 3 files:')
  cat('\n\t 1-: Connection_list: Adjacency matrix that contains the network structure;')
  cat('\n\t 2-: Weight: Indexes of each vertex contained in the network.')
  cat('\n\t 3-: Hittrue: vertices that have been selected to compose the active modules.')
  cat("\n -o: Directory to receive the GIGA results.")
  cat("\n --giga: Address of giga tool.")
  cat("\n --genes: List of all hugo genes (.csv).")
  cat("\n --th: threshold parameter to determine the size of output.\n\n")
  
  cat("Ex: Rscript GIGA_test.R -f /FILES_PATH/ -o /OUTPUT_PATH/output_name.csv --giga /GIGA_PATH/GiGA.pl --genes /GENES_PATH/genes_hugo.csv --th 50\n\n")
  
}else{
  ## It is important to install these libraries before run this script
  library(dplyr)
  library(magrittr)
  library(igraph) 
  
  th = 50  # threshold parameter to determine the size of output
  if("-f" %in% args){
    arg.files <-  which(args == "-f") + 1
    FILES_PATH <- as.character(args[arg.files])
  }
  if("-o" %in% args){
    arg.output <-  which(args == "-o") + 1
    OUTPUT_PATH <- as.character(args[arg.output])
    aux <- strsplit(OUTPUT_PATH,"/")[[1]]
    remov <- aux[length(aux)]
    OUT_PATH <- gsub(remov,"\\1",OUTPUT_PATH)
    INPUT_PATH <- paste0(OUT_PATH,"input_giga.txt")
    INPUT_NET <- paste0(OUT_PATH,"graph.txt")
    TEMP_PATH <- paste0(OUT_PATH,"temp.txt")
  }
  if("--th" %in% args){
    arg.th <-  which(args == "--th") + 1
    th <- as.numeric(as.character(args[arg.th]))
  }
  if("--giga" %in% args){
    arg.giga <-  which(args == "--giga") + 1
    GIGA_PATH <- as.character(args[arg.giga])
  }
  if("--genes" %in% args){
    arg.gene <-  which(args == "--genes") + 1
    GENE_PATH <- as.character(args[arg.gene])
  }
  ## numer of '_' in the files + 1
  ax = 2
  ########################################################################################################
  genesname <- read.csv(file = GENE_PATH)
  genesname <- as.character(genesname$V2)
  
  ## ordering the files
  files <- list.files(FILES_PATH)
  index <- NULL
  for(i in 1:length(files)){
    f <- files[i]
    aux <- strsplit(f,"_")[[1]][1]
    aux <- gsub("sim","\\1",aux)
    index[i] <- gsub("[.]","\\1",aux)
  }
  index <- as.numeric(index)
  ord <- order(index, decreasing = F)
  files <- files[ord]
  
  ## identifying: network, pvalues and hits.
  net <- NULL; pvalue <- NULL; hits <- NULL
  for(i in 1:length(files)){
    f <- files[i]
    verification <- strsplit(f,"_")[[1]][ax]
    if(verification == "connection"){
      net <- c(net,i)
    }else if(verification == "hittrue.csv"){
      hits <- c(hits,i)
    }else if(verification == "weight.csv"){
      pvalue <- c(pvalue,i)
    }
  }
  NETWORK <- files[net]
  HITS <- files[hits]
  PVALUES <- files[pvalue]
  
  ## Identifying the COSINE recall based on Robinson's (2017) results
  giga_results <- NULL
  for(f in 1:length(NETWORK)){
    ## upload network
    network_path <- paste0(FILES_PATH,NETWORK[f])
    matrix_adj <- read.csv(file = network_path, header = F)
    matrix_adj <- as.matrix(matrix_adj)
    namess <- genesname[1:nrow(matrix_adj)]
    rownames(matrix_adj) <- namess
    colnames(matrix_adj) <- namess
    
    ## upload true hits
    hit_path <- paste0(FILES_PATH,HITS[f])
    truehits <- read.csv(file = hit_path, header = F)
    truehits <- truehits$V1 + 1 # because it starts from 0 in python, and in 1 R starts from 1.
    truehits <- namess[truehits]
    
    ## upload pvalues
    pvalues_path <- paste0(FILES_PATH,PVALUES[f])
    transcript <- read.csv(file = pvalues_path, header = F)
    transcript <- transcript$V1
    names(transcript) <- namess
    transcript <- 1 - transcript
    
    set <- strsplit(HITS[f],"_")[[1]][1]
    
    ## Create ppi network ####
    ppi <- graph.adjacency(as.matrix(matrix_adj), weighted = NULL, mode = "directed")
    
    ## Identifying PPI network
    edges = get.edgelist(ppi)
    node1 <- NULL; node2 <- NULL
    for(i in 1:nrow(edges)){
      x1 <- edges[i,1]
      x2 <- edges[i,2]
      i1 <- which(node2 == x1)
      i2 <- which(node1 == x2)
      test <- intersect(i1,i2)
      if(length(test) == 0){
        node1 <- c(node1,x1)
        node2 <- c(node2,x2)
      }
    }
    PPI <- cbind(node1,node2)
  
    write.table(PPI, file = INPUT_NET,
                quote = FALSE, sep = "\t", row.names = FALSE)
    
    genes <- names(transcript)
    test.rp <- as.numeric(transcript * 10^4)
    ranks <- rank(test.rp)
    input_giga <- cbind(genes,as.numeric(test.rp),as.numeric(ranks))
    colnames(input_giga) <- c("genes", "rank.prod", "ranks")
    input_giga <- input_giga[order(ranks),]
  
    write.table(input_giga, file = INPUT_PATH,
              quote = FALSE, sep = "\t", row.names = FALSE)
    
    sys.text <- paste("perl ", GIGA_PATH, " -i", INPUT_PATH, 
                      " -n", INPUT_NET, " -Ftxt", " -t", 1, " -m", th, " -o", TEMP_PATH, sep="");
    system(sys.text)
    
    test <- readLines(TEMP_PATH)
    paths <- which(1:length(test)%in%grep("^-", test)==F)[1:2];
    genes <- toString(unlist(do.call(rbind,sapply(test[(paths[1] + 1):(paths[2] - 1)], FUN=function(x)strsplit(x, "\t")))[,2]))
    selected <- strsplit(genes,",")[[1]]
    selected <- gsub(" ", "", selected, fixed = TRUE)
    
    tp <- length(intersect(selected,truehits))
    fp <- length(setdiff(selected,truehits))
    fn <- length(truehits) - tp
    recall <- tp/(tp+fn) 
    precision <- tp/(tp+fp)
    f1_score <- 2 * ((precision * recall)/(precision + recall))
    aux <- c(fn,tp,fp,recall,precision,f1_score)
    names(aux) <- c("fn","tp","fp","recall","precision","f1_score")
    giga_results <- rbind(giga_results, aux)
    print(tail(giga_results))
    rownames(giga_results)[f] <- set
    write.csv(giga_results,file = OUTPUT_PATH)
  } 
}
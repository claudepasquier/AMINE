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
if("BioNet" %in% rownames(installed.packages()) == FALSE) {
  if (!requireNamespace("BiocManager", quietly = TRUE))
    install.packages("BiocManager")
  
  BiocManager::install("BioNet")
}

args <- commandArgs(trailingOnly = TRUE)

if("--help" %in% args){
  system("clear")
  cat('\nPARAMETER OPTIONS:\n')
  cat('\n -f: Directory containing simulated networks. Each network is represented by 3 files:')
  cat('\n\t 1-: Connection_list: Adjacency matrix that contains the network structure;')
  cat('\n\t 2-: Weight: Indexes of each vertex contained in the network.')
  cat('\n\t 3-: Hittrue: vertices that have been selected to compose the active modules.')
  cat("\n -o: Directory to receive the BioNet results.")
  cat("\n --fdrs: BioNet parameter, default = 0.001.\n\n")

  cat("Ex: Rscript BIONET_test.R -f /FILES_PATH/ -o /OUTPUT_PATH/ --fdrs 0.001\n\n")
  
}else {
  ## It is important to install these libraries before run this script
  library(dplyr)
  library(magrittr)
  library(igraph)  
  library(BioNet)
  
  fdrs = 0.001
  if("-f" %in% args){
    arg.files <-  which(args == "-f") + 1
    FILES_PATH <- as.character(args[arg.files])
  }
  if("-o" %in% args){
    arg.output <-  which(args == "-o") + 1
    OUTPUT_PATH <- as.character(args[arg.output])
    OUTPUT_PATH <- paste0(OUTPUT_PATH,"BioNet_results.csv")
  }
  if("--fdrs" %in% args){
    arg.fdrs <-  which(args == "--fdrs") + 1
    fdrs <- as.numeric(as.character(args[arg.fdrs]))
  }
  ## numer of '_' in the files + 1
  ax = 2
########################################################################################################
  minMax <- function(vet, min=-1.653694, max=4.246089){
    v_n <- NULL
    for(i in 1:length(vet)){
      v_n[i] <- min + (vet[i] - min(vet))/(max(vet) - min(vet)) *   (max-min)
      v_n[i] <- round(v_n[i], 3)
    }
    
    return(v_n)
  }
  
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
  bionet_results <- NULL
  for(f in 1:length(NETWORK)){
    ## upload network
    network_path <- paste0(FILES_PATH,NETWORK[f])
    matrix_adj <- read.csv(file = network_path, header = F)
    matrix_adj <- as.matrix(matrix_adj)
    namess <- 1:nrow(matrix_adj)
    rownames(matrix_adj) <- namess
    colnames(matrix_adj) <- namess
    
    ## upload true hits
    hit_path <- paste0(FILES_PATH,HITS[f])
    truehits <- read.csv(file = hit_path, header = F)
    truehits <- truehits$V1 + 1 # because it starts from 0 in python, and in 1 R starts from 1.
    
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
    PPI <- cbind(as.numeric(node1),as.numeric(node2))
    
    subnet <- igraph.to.graphNEL(graph.data.frame(PPI, directed=F))
    subnet <- rmSelfLoops(subnet)
    fb <- fitBumModel(transcript, plot=FALSE)
    scores <- scoreNodes(subnet, fb, fdr=fdrs)
    if(length(scores[which(scores > 0)]) == 0){
      nm <- names(scores)
      scores <- minMax(scores)
      names(scores) <- nm 
      set <- paste0("*",set)
    }
    module <- try(runFastHeinz(subnet, scores))
    if("try-error" %in% class(module)){
      selected <- NULL
    } else{
      selected <- module@nodes 
    }
    tp <- length(intersect(as.numeric(selected),truehits))
    fp <- length(setdiff(as.numeric(selected),truehits))
    fn <- length(truehits) - tp
    recall <- tp/(tp+fn) 
    precision <- tp/(tp+fp)
    f1_score <- 2 * ((precision * recall)/(precision + recall))
    aux <- c(fn,tp,fp,recall,precision,f1_score)
    names(aux) <- c("fn","tp","fp","recall","precision","f1_score")
    bionet_results <- rbind(bionet_results, aux)
    print(tail(bionet_results))
    rownames(bionet_results)[f] <- set
    write.csv(bionet_results,file = OUTPUT_PATH)
  } 
}
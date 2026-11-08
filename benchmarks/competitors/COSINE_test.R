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
if("COSINE" %in% rownames(installed.packages()) == FALSE) {
  cat("\nInstalling COSINE R package...\n")
  install.packages("COSINE")
}

args <- commandArgs(trailingOnly = TRUE)

if("--help" %in% args){
  system("clear")
  cat('\nPARAMETER OPTIONS:\n')
  cat('\n -f: Directory containing simulated networks. Each network is represented by 3 files:')
  cat('\n\t 1-: Connection_list: Adjacency matrix that contains the network structure;')
  cat('\n\t 2-: Weight: Indexes of each vertex contained in the network.')
  cat('\n\t 3-: Hittrue: vertices that have been selected to compose the active modules.')
  cat("\n -o: Directory to receive the COSINE results.")
  cat("\n --min: The minimal size of clusters (COSINE parameter).")
  cat("\n --int: Number of generations in the GA (COSINE parameter).\n\n")
  
  cat("Ex: Rscript COSINE_test.R -f /FILES_PATH/ -o /OUTPUT_PATH/ --min 10 --int 300\n\n")
  
}else {
  ## It is important to install these libraries before run this script
  library(dplyr)
  library(magrittr)
  library(igraph)
  library(COSINE)
  
  minSize = 10; n_iter = 100
  if("-f" %in% args){
    arg.files <-  which(args == "-f") + 1
    FILES_PATH <- as.character(args[arg.files])
  }
  if("-o" %in% args){
    arg.output <-  which(args == "-o") + 1
    OUTPUT_PATH <- as.character(args[arg.output])
    OUTPUT_PATH <- paste0(OUTPUT_PATH,"COSINE_results.csv")
  }
  if("--min" %in% args){
    arg.min <-  which(args == "--min") + 1
    minSize <- as.numeric(as.character(args[arg.min]))
  }
  if("--int" %in% args){
    arg.int <-  which(args == "--int") + 1
    n_iter <- as.numeric(as.character(args[arg.int]))
  }
  ## numer of '_' in the files + 1
  ax = 2
########################################################################################################

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
  cosine_results <- NULL
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
    transcript <- 1 - transcript
    names(transcript) <- namess
    
    ## Preprocessing data for COSINE tool execution
    ## Create ppi network ####
    ppi <- graph.adjacency(as.matrix(matrix_adj), weighted = NULL, mode = "directed")
    #plot_g(ppi,as.character(truehits))
    
    ## Fv = 1 - simulated p-value
    fv <- 1 - as.numeric(transcript)
    
    ## Initialize network weight
    V(ppi)$fc <- rep(0,length(V(ppi)$name))
    
    ## Calculate scaled Nodescore
    scaled_node_score <- NULL
    for(i in 1:length(transcript)){
      fv_i <- fv[i]
      ## Nodescore = Fv - mean(Fv) / stardad deviton(Fv)
      scaled_node_score[i] <- (fv_i - mean(fv)) / sd(fv)
      V(ppi)$fc[i] <- scaled_node_score[i]
    }
    names(scaled_node_score) <- names(transcript)
    
    ## Identifying PPI network
    edges = get.edgelist(ppi)
    e1 <- NULL; e2 <- NULL
    for(i in 1:nrow(edges)){
      x1 <- edges[i,1]
      x2 <- edges[i,2]
      i1 <- which(e2 == x1)
      i2 <- which(e1 == x2)
      test <- intersect(i1,i2)
      if(length(test) == 0){
        e1 <- c(e1,x1)
        e2 <- c(e2,x2)
      }
    }
    PPI <- cbind(as.numeric(e1),as.numeric(e2))
    
    ## Calculate scaled Edgescore
    edgescore <- NULL
    for(i in 1:nrow(PPI)){
      index_ey <- which(names(scaled_node_score) == as.character(PPI[i,1]))
      index_ex <- which(names(scaled_node_score) == as.character(PPI[i,2]))
      ey <- scaled_node_score[index_ey]
      ex <- scaled_node_score[index_ex]
      edgescore[i] <- (ey + ex) / 2
    }
    scaled_edge_score <- NULL
    for(i in 1:length(edgescore)){
      ecf_i <- edgescore[i]
      ## Edgescore = ECF(e) - mean(ECF) / stardad deviton(ECF)
      scaled_edge_score[i] <- (ecf_i - mean(edgescore)) / sd(edgescore)
    }
    
    ## Choice the best lambda
    klist <- minSize; pop_size <- 100
    quantiles <- get_quantiles_PPI(scaled_node_score, scaled_edge_score, PPI, klist, pop_size)
    lambda <- quantiles[[2]]
    
    ## Exectue COSINE for the 5 best lambdas
    best_score <- 0
    for(i in 1:length(lambda)){
      lbd <- lambda[i]
      GA_result <- GA_search_PPI(lambda=lbd,scaled_node_score,scaled_edge_score,PPI,
                                 num_iter=n_iter, muCh=0.05, zToR=10, minsize=minSize)
      
      bsscore <- GA_result$Best_Scores
      if(bsscore > best_score){
        ## Best COSINE results 
        subnet <- GA_result$Subnet
        tp <- length(intersect(subnet,truehits))
        fp <- length(setdiff(subnet,truehits))
        best_score <- bsscore
      }
    }
    
    ## Note the results based in the best lambda value
    fn <- length(truehits) - tp
    recall <- tp/(tp+fn) 
    precision <- tp/(tp+fp)
    f1_score <- 2 * ((precision * recall)/(precision + recall))
    aux <- c(fn,tp,fp,recall,precision,f1_score)
    names(aux) <- c("fn","tp","fp","recall","precision","f1_score")
    cosine_results <- rbind(cosine_results, aux)
    print(tail(cosine_results))
    rownames(cosine_results)[f] <- strsplit(HITS[f],"_")[[1]][1]
    write.csv(cosine_results,file = OUTPUT_PATH)
  }
}
if [ ! -n $AMINE_DATA ]; then
	AMINE_DATA=./data
fi

STRING_VERSION=v11.0
for specie in 9606 7227 10090 6239
do
	FILENAME=${specie}.protein.links.detailed.${STRING_VERSION}.txt.gz
	curl "https://stringdb-static.org/download/protein.links.detailed.${STRING_VERSION}/${FILENAME}" -o ${AMINE_DATA}/${FILENAME}
	FILENAME=${specie}.protein.info.${STRING_VERSION}.txt.gz
	curl "https://stringdb-static.org/download/protein.info.${STRING_VERSION}/${FILENAME}" -o ${AMINE_DATA}/${FILENAME}
	FILENAME=${specie}.protein.aliases.${STRING_VERSION}.txt.gz
	curl "https://stringdb-static.org/download/protein.aliases.${STRING_VERSION}/${FILENAME}" -o ${AMINE_DATA}/${FILENAME}
done


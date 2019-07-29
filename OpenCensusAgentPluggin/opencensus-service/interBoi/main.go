package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"net"
	"time"
)

type mdsdJSON struct {
	Tag    string   `json:"TAG"`
	Source string   `json:"SOURCE"`
	Data   []string `json:"DATA"`
}

func main() {
	fmt.Println("Starting funnel of data.")

	conn, err := net.Dial("unix", "/var/run/mdsd/default_json.socket")
	if err != nil {
		fmt.Printf("Error connecting %v", err)
		return
	}

	for {
		time.Sleep(time.Second * 3)
		id := "7"         //time.Now().UTC()
		resultTime := "7" //id.Format(time.RFC3339)

		dataList := []string{
			resultTime, //Timestamp
			"okay",     // status
		}
		log := new(mdsdJSON)

		log.Tag = id //strconv.FormatInt(id.Unix(), 10)
		log.Source = "funnel"
		log.Data = dataList
		byteData, _ := json.Marshal(log)

		_, err = conn.Write(byteData)

		r := bufio.NewReader(conn)
		line, err := r.ReadString('\n')
		if err != nil {
			fmt.Printf("error reading, %v", err)
			return
		}
		fmt.Println("pollo was here")
		fmt.Println(line)

	}

}

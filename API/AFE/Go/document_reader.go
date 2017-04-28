package main

// =============================================================
// AFE Nav API sample:
// 1) login to API
// 2) search for AFE identified on command line
// 3) retrieve AFE data and print number, description and total gross estimate
// 4) logout
// =============================================================

import (
  "bytes"
  "crypto/tls"
  "encoding/json"
  "errors"
  "flag"
  "fmt"
  "github.com/BurntSushi/toml"
  "io"
  "net/http"
  "time"
)

// Config represents the configuration for an AFE Nav with user credentials
type Config struct {
  Url                string
  Username           string
  Password           string
  InsecureSkipVerify bool
}

// AfeNavService represents an instance of an AFE Navigator service with configuration and state
type AfeNavService struct {
  Config              Config
  AuthenticationToken string
}

type LoginRequest struct {
  Username string `json:"UserName"`
  Password string
}

type LoginResponse struct {
  AuthenticationToken string
}

type SearchAndOpenRequest struct {
  DocumentType        string
  SearchString        string
  AuthenticationToken string
}

type OpenResponse struct {
  DocumentHandle string
}

type AuthenticationTokenRequest struct {
  AuthenticationToken string
}

type DocumentHandleRequest struct {
  AuthenticationToken string
  DocumentHandle      string
}

type DocumentReadRequest struct {
  AuthenticationToken    string
  DocumentHandle         string
  SerializeDocumentTypes []string
}

type UwiValue struct {
  Value     string
  SortedUwi string
  UwiType   string
}

type DocumentId string

type DocumentField struct {
  Id                 string
  Text               string
  Bool               bool
  NumberDecimal      float64
  NumberInteger      int
  Date               time.Time
  Uwi                UwiValue
  Guid               string
  Document           DocumentId
  DocumentDescriptor string
  Record             DocumentRecord
  Records            []DocumentRecord
  FileSize           int64
  FileType           string
  FileVersionNumber  int32
}

type DocumentRecord struct {
  Fields []DocumentField
}

func (record DocumentRecord) Field(id string) (*DocumentField, error) {
  for _, f := range record.Fields {
    if f.Id == id {
      return &f, nil
    }
  }
  return nil, errors.New("Field Not Found")
}

type DocumentData struct {
  DocumentId   DocumentId
  DocumentType string
  Record       DocumentRecord
}

func (doc DocumentData) Field(id string) (*DocumentField, error) {
  return doc.Record.Field(id)
}

type DocumentReadResponse struct {
  BaseDocument   DocumentData
  ChildDocuments []DocumentData
}

func (r DocumentReadResponse) ChildDocument(id DocumentId) (*DocumentData, error) {
  for _, d := range r.ChildDocuments {
    if d.DocumentId == id {
      return &d, nil
    }
  }
  return nil, errors.New("Document not found")
}

// AfeNavError is the standard format for unexprected exceptions from AFE Nav
type AfeNavError struct {
  ClassName string
  Message   string
}

type DocumentHandle string

func (service *AfeNavService) call(api string, request []byte) (io.ReadCloser, error) {

  // TLS configuration to bypass TLS check if we are using a self-signed cert
  tls := &tls.Config{
    InsecureSkipVerify: service.Config.InsecureSkipVerify,
  }

  tr := &http.Transport{
    MaxIdleConns:    10,
    IdleConnTimeout: 30 * time.Second,
    TLSClientConfig: tls,
  }

  client := &http.Client{Transport: tr}

  req, _ := http.NewRequest("POST", service.Config.Url+api, bytes.NewReader(request))
  req.Header.Add("Content-type", "application/json")

  resp, err := client.Do(req)
  if err != nil {
    return nil, err
  }

  if resp.StatusCode == http.StatusInternalServerError {
    // If we get a 500, decode the result and parse into an AfeNavError object
    var afeNavError AfeNavError
    decoder := json.NewDecoder(resp.Body)
    err = decoder.Decode(&afeNavError)
    if err != nil {
      return nil, err
    }
    return nil, errors.New(afeNavError.Message)
  }

  return resp.Body, nil
}

// Login opens a session against the AFE Navigator service and stores the authenticationToken
func (service *AfeNavService) Login() error {
  request, _ := json.Marshal(LoginRequest{
    Username: service.Config.Username,
    Password: service.Config.Password,
  })

  responseReader, err := service.call("/api/Authentication/Login", request)
  if err != nil {
    return err
  }
  defer responseReader.Close()

  var response LoginResponse
  decoder := json.NewDecoder(responseReader)
  err = decoder.Decode(&response)
  if err != nil {
    return err
  }

  service.AuthenticationToken = response.AuthenticationToken

  return nil
}

// SearchAndOpenReadonly searchs for and opens a readonly handle to a document of a given type
func (service *AfeNavService) SearchAndOpenReadonly(documentType string, searchString string) (DocumentHandle, error) {
  request, _ := json.Marshal(SearchAndOpenRequest{
    AuthenticationToken: service.AuthenticationToken,
    DocumentType:        documentType,
    SearchString:        searchString,
  })

  responseReader, err := service.call("/api/Documents/SearchAndOpenReadonly", request)
  if err != nil {
    return "", err
  }
  defer responseReader.Close()

  var response OpenResponse
  decoder := json.NewDecoder(responseReader)
  err = decoder.Decode(&response)
  if err != nil {
    return "", err
  }

  return DocumentHandle(response.DocumentHandle), nil
}

// SearchAndOpenReadonly searchs for and opens a readonly handle to a document of a given type
func (service *AfeNavService) ReadDocument(handle DocumentHandle, serializeDocumentTypes []string) (*DocumentReadResponse, error) {
  request, _ := json.Marshal(DocumentReadRequest{
    AuthenticationToken:    service.AuthenticationToken,
    DocumentHandle:         string(handle),
    SerializeDocumentTypes: serializeDocumentTypes,
  })

  responseReader, err := service.call("/api/Documents/Read", request)
  if err != nil {
    return nil, err
  }
  defer responseReader.Close()

  var response DocumentReadResponse
  decoder := json.NewDecoder(responseReader)
  err = decoder.Decode(&response)
  if err != nil {
    return nil, err
  }

  return &response, nil
}

// Close a document handle!
func (service *AfeNavService) CloseDocument(handle DocumentHandle) error {
  request, _ := json.Marshal(DocumentHandleRequest{
    AuthenticationToken: service.AuthenticationToken,
    DocumentHandle:      string(handle),
  })

  responseReader, err := service.call("/api/Documents/Close", request)
  if err != nil {
    return err
  }
  responseReader.Close()

  return nil
}

// Logout terminates the active session and erases the authenticationToken
func (service *AfeNavService) Logout() error {
  if service.AuthenticationToken == "" {
    return errors.New("Not logged in")
  }
  request, _ := json.Marshal(AuthenticationTokenRequest{
    AuthenticationToken: service.AuthenticationToken,
  })

  _, err := service.call("/api/Authentication/Logout", request)
  if err != nil {
    return err
  }

  service.AuthenticationToken = ""
  return nil
}

func main() {

  searchString := flag.String("search", "", "search string")
  flag.Parse()

  // print usage if search string not provided
  if *searchString == "" {
    flag.Usage()
    return
  }

  var config Config

  // read configuration
  if _, err := toml.DecodeFile("document_reader.config", &config); err != nil {
    panic(err)
  }

  // create instance of the AFE Nav service
  var service AfeNavService
  service.Config = config

  // login
  if err := service.Login(); err != nil {
    panic(err)
  }
  defer service.Logout()

  // open document handle for AFE
  handle, err := service.SearchAndOpenReadonly("AFE", *searchString)
  if err != nil {
    panic(err)
  }
  defer service.CloseDocument(handle)

  // Read the AFE document
  doc, err := service.ReadDocument(handle, []string{"AFE", "AFENUMBER"})
  if err != nil {
    panic(err)
  }

  // print out the AFE Number
  afeNumberDocId, _ := doc.BaseDocument.Field("AFENUMBER_DOC")
  afeNumberDoc, _ := doc.ChildDocument(afeNumberDocId.Document)
  if f, err := afeNumberDoc.Field("AFENUMBER"); err == nil {
    fmt.Println("AFE Number: ", f.Text)
  }

  // print out the AFE Description
  if f, err := doc.BaseDocument.Field("DESCRIPTION"); err == nil {
    fmt.Println("Description: ", f.Text)
  }

  // print out total gross estimate
  if f, err := doc.BaseDocument.Field("TOTAL_GROSS_ESTIMATE"); err == nil {
    fmt.Println("Total Gross Estimate: ", f.NumberDecimal)
  }

}

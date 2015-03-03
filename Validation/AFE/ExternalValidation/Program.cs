using System;
using System.Collections.Generic;
using System.Linq;
using System.Xml.Linq;

namespace ExternalValidation
{
    class Program
    {
        static int Main(string[] args)
        {
            XElement afeXml;
            try { afeXml = XElement.Load(args[0]); }
            catch { return 1; }
            XNamespace afeNS = "http://energynavigator.com/xml/afe/2";
            XNamespace eventNS = "http://energynavigator.com/xml/afe/validate/2";

            XElement afeElement = afeXml.Element(eventNS + "AFE");
            XElement documentElement = afeElement.Element(afeNS + "DocumentData");

            XElement startDateElement = null, endDateElement = null, descriptionElement = null;
            if (documentElement != null)
            {
                descriptionElement = documentElement.Element(afeNS + "DESCRIPTION");
                startDateElement = documentElement.Element(afeNS + "START_DATE");
                endDateElement = documentElement.Element(afeNS + "END_DATE");
            }
            if (descriptionElement == null || startDateElement == null || endDateElement == null) { return 2; }

            List<string> warnings = new List<string>();
            List<string> errors = new List<string>();
            if (string.IsNullOrEmpty(startDateElement.Value))
            {
                errors.Add("Start date must be filled out");
            }
            if (string.IsNullOrEmpty(endDateElement.Value))
            {
                errors.Add("End date must be filled out");
            }
            if (errors.Count == 0)
            {
                DateTime startDate = DateTime.Parse(startDateElement.Value);
                DateTime endDate = DateTime.Parse(endDateElement.Value);
                if (endDate < startDate)
                {
                    errors.Add("End date must be equal to or after start date");
                }
            }

            if (string.IsNullOrEmpty(descriptionElement.Value) ||
                descriptionElement.Value.IndexOf("please", StringComparison.InvariantCultureIgnoreCase) < 0)
            {
                warnings.Add("Description should contain the word 'please'");
            }

            XNamespace resultNS = "http://energynavigator.com/xml/afe/validate-result/2";
            XElement response = new XElement(resultNS + "AFEValidateResult");
            if (errors.Count == 0)
            {
                response.Add(new XElement(resultNS + "Success"));
            }
            else
            {
                response.Add(new XElement(resultNS + "Failure", errors.Select(x => new XElement(resultNS + "ValidationErrorMessage", x))));
            }

            if (warnings.Count != 0)
            {
                response.Add(new XElement(resultNS + "Warnings", warnings.Select(x => new XElement(resultNS + "ValidationWarningMessage", x))));
            }
            try { response.Save(args[1]); }
            catch { return 3; }
            return 0;
        }
    }
}
